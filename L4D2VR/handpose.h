#pragma once
#include "sdk/vector.h"
#include <cmath>
#include <cstring>

namespace HandPose {
enum class Model { Other, Gun, Hands };
inline Model Identify(const char *name, int boneCount) {
    if (boneCount == 45 && !_strnicmp(name, "weapons/v_portalgun.mdl", 64)) return Model::Gun;
    if (boneCount == 43 && !_strnicmp(name, "weapons/v_hands.mdl", 64)) return Model::Hands;
    return Model::Other;
}
// Change a rigid bone's coordinate frame without changing its animated pose.
inline matrix3x4_t Reanchor(const matrix3x4_t& bone,
    const matrix3x4_t& source, const matrix3x4_t& target)
{
    matrix3x4_t result;
    float rotation[3][3]{};
    for (int row = 0; row < 3; ++row)
        for (int col = 0; col < 3; ++col)
            for (int k = 0; k < 3; ++k)
                rotation[row][col] += target[row][k] * source[col][k];
    for (int row = 0; row < 3; ++row) {
        for (int col = 0; col < 3; ++col) {
            result[row][col] = 0;
            for (int k = 0; k < 3; ++k)
                result[row][col] += rotation[row][k] * bone[k][col];
        }
        result[row][3] = target[row][3];
        for (int k = 0; k < 3; ++k)
            result[row][3] += rotation[row][k] * (bone[k][3] - source[k][3]);
    }
    return result;
}

inline matrix3x4_t Frame(const Vector& x, const Vector& y, const Vector& z, const Vector& position)
{
    return matrix3x4_t(x.x,y.x,z.x,position.x, x.y,y.y,z.y,position.y, x.z,y.z,z.z,position.z);
}

inline matrix3x4_t Concat(const matrix3x4_t& parent, const matrix3x4_t& local)
{
    matrix3x4_t result;
    for (int row = 0; row < 3; ++row) {
        for (int col = 0; col < 3; ++col) {
            result[row][col] = 0;
            for (int k = 0; k < 3; ++k) result[row][col] += parent[row][k] * local[k][col];
        }
        result[row][3] = parent[row][3];
        for (int k = 0; k < 3; ++k) result[row][3] += parent[row][k] * local[k][3];
    }
    return result;
}

inline matrix3x4_t FitGunToPalm(const matrix3x4_t& gun)
{
    // Uniform weapon scale makes room for the full-size paw inside the housing.
    // The tracked wrist stays fixed. Attachments use this same fitted frame.
    return Concat(gun, Frame({1.2f,0,0}, {0,1.2f,0}, {0,0,1.2f}, {.218f,-7.66f,-3.3f}));
}

inline matrix3x4_t RigidOrientation(matrix3x4_t frame) {
    // A support hand follows the scaled socket position, retaining hand size.
    for (int c=0;c<3;++c) {
        const float length = sqrtf(frame[0][c]*frame[0][c]+frame[1][c]*frame[1][c]+frame[2][c]*frame[2][c]);
        if (length>1e-8f) for (int r=0;r<3;++r) frame[r][c]/=length;
    }
    return frame;
}

// The rebuilt mesh uses +X toward the fingers and +Y toward the thumb.
// Flip both lateral axes around forward so the palms face the controller grip.
inline matrix3x4_t ControllerHandFrame(const Vector& forward, const Vector& right,
    const Vector& up, const Vector& position, bool left)
{
    return Frame(forward, left ? right : -right, left ? -up : up, position);
}

inline matrix3x4_t InverseRigid(const matrix3x4_t& matrix) {
    matrix3x4_t result;
    for (int row = 0; row < 3; ++row) {
        for (int col = 0; col < 3; ++col) result[row][col] = matrix[col][row];
        result[row][3] = 0;
        for (int col = 0; col < 3; ++col) result[row][3] -= matrix[col][row] * matrix[col][3];
    }
    return result;
}

inline void AlignBareArms(const matrix3x4_t *bones, matrix3x4_t *result,
    const matrix3x4_t& leftTarget, const matrix3x4_t& rightTarget)
{
    // Use the model's bind skeleton consistently; this custom hand model's
    // finger geometry is authored in that frame and inherited player bones
    // distort the finger chain when copied into VR.
    for (int i = 5; i < 24; ++i) result[i] = Reanchor(bones[i], bones[8], leftTarget);
    for (int i = 24; i < 43; ++i) result[i] = Reanchor(bones[i], bones[27], rightTarget);
}

// Build an active rotation around an arbitrary axis.  Finger joints in the
// custom VPK do not all use the wrist's canonical Y axis; using one fixed
// matrix makes the index through pinky twist sideways and makes the thumb
// curl into the palm.  The columns match matrix3x4_t's local X/Y/Z axes.
inline matrix3x4_t RotateAroundAxis(Vector axis, float radians)
{
    const float lengthSqr = axis.LengthSqr();
    if (lengthSqr <= 1e-8f)
        return Frame({1,0,0}, {0,1,0}, {0,0,1}, {0,0,0});

    axis *= 1.0f / sqrtf(lengthSqr);
    const float x = axis.x;
    const float y = axis.y;
    const float z = axis.z;
    const float c = cosf(radians);
    const float s = sinf(radians);
    const float t = 1.0f - c;

    return Frame(
        {t*x*x + c,     t*x*y + s*z, t*x*z - s*y},
        {t*x*y - s*z,   t*y*y + c,   t*y*z + s*x},
        {t*x*z + s*y,   t*y*z - s*x, t*z*z + c},
        {0,0,0});
}

inline matrix3x4_t FingerBend(float radians)
{
    // The custom VPK finger bones run down local +X.  Local +Z is the back of
    // the hand, so the knuckle hinge is local Y: rotating around Z only turns
    // the fingers sideways and produces the user's karate-chop pose.  Positive
    // Y rotation sends +X toward the palm (-Z); the mirrored wrist frame makes
    // the same local pose correct for both hands.
    return RotateAroundAxis({0,1,0}, radians);
}

// A skeletal joint rotates at its own origin. Applying the active rotation
// to the full parent-to-child matrix also rotates the child translation around
// its parent, which makes every knuckle orbit the wrist and collapses the
// fingers into one stack. Rotate only the basis and retain the authored joint
// position.
inline matrix3x4_t RotateJoint(const matrix3x4_t& local, const Vector& axis,
    float radians)
{
    matrix3x4_t result = Concat(RotateAroundAxis(axis, radians), local);
    for (int row = 0; row < 3; ++row)
        result[row][3] = local[row][3];
    return result;
}

inline void ApplyFingerCurlChain(const matrix3x4_t *bind, matrix3x4_t *result,
    const float *curl, int offset, int wrist, bool left = true,
    const float *gripFlexion = nullptr)
{
    static const int chains[5][3] = {
        {21,22,23}, {18,19,20}, {15,16,17}, {12,13,14}, {9,10,11}
    };
    const Vector forward(bind[wrist][0][0], bind[wrist][1][0], bind[wrist][2][0]);
    const Vector palm = Vector(bind[wrist][0][2], bind[wrist][1][2], bind[wrist][2][2])
        * (left ? 1.0f : -1.0f);
    const float openHandFlexion[3] = {0.70f, 0.80f, 0.45f};
    const float *flexion = gripFlexion ? gripFlexion : openHandFlexion;
    const float thumbFlexion[3] = {0.10f, 0.22f, 0.18f};
    for (int finger = 0; finger < 5; ++finger) {
        // Zero is an open hand. Invalid input cannot enter the bone palette.
        const float amount = std::isfinite(curl[finger])
            ? fmaxf(0.0f, fminf(1.0f, curl[finger])) : 0.0f;
        int parent = wrist;
        for (int segment = 0; segment < 3; ++segment) {
            const int bone = chains[finger][segment] + offset;
            const int from = segment < 2 ? bone : parent;
            const int to = segment < 2 ? chains[finger][segment + 1] + offset : bone;
            const Vector direction(bind[to][0][3] - bind[from][0][3],
                bind[to][1][3] - bind[from][1][3], bind[to][2][3] - bind[from][2][3]);
            // Derive the hinge from anatomical joint positions, independently
            // of the model's bone roll. The thumb wraps toward the fingers
            // in the palm plane, staying outside the curled finger volume.
            const Vector toward = finger == 0 ? forward : palm;
            const Vector axis(direction.y*toward.z - direction.z*toward.y,
                direction.z*toward.x - direction.x*toward.z,
                direction.x*toward.y - direction.y*toward.x);
            const auto inverseParent = InverseRigid(bind[parent]);
            const Vector localAxis(
                inverseParent[0][0]*axis.x + inverseParent[0][1]*axis.y + inverseParent[0][2]*axis.z,
                inverseParent[1][0]*axis.x + inverseParent[1][1]*axis.y + inverseParent[1][2]*axis.z,
                inverseParent[2][0]*axis.x + inverseParent[2][1]*axis.y + inverseParent[2][2]*axis.z);
            const auto local = Concat(inverseParent, bind[bone]);
            auto bent = RotateJoint(local, localAxis,
                amount * (finger == 0 ? thumbFlexion[segment] : flexion[segment]));
            // The broad paw pads need a little knuckle splay while closing.
            // Rotate at the joint; never translate the authored knuckle.
            if (segment == 0 && (finger == 1 || finger == 3))
                bent = RotateJoint(bent, {0,0,1}, amount * (finger == 1 ? 0.18f : -0.18f));
            result[bone] = Concat(result[parent], bent);
            parent = bone;
        }
    }
}

inline void ApplyFingerCurl(const matrix3x4_t *bind, matrix3x4_t *result,
    const float *leftCurl, const float *rightCurl)
{
    ApplyFingerCurlChain(bind, result, leftCurl, 0, 8, true);
    ApplyFingerCurlChain(bind, result, rightCurl, 19, 27, false);
}

inline void SeatGunHand(matrix3x4_t *bones) {
    const auto gun = RigidOrientation(bones[24]);
    const Vector x(gun[0][0],gun[1][0],gun[2][0]);
    const Vector up(gun[0][1],gun[1][1],gun[2][1]);
    const Vector forward(gun[0][2],gun[1][2],gun[2][2]);
    constexpr float radians = 0.017453292519943295f;
    const auto rotation = Concat(RotateAroundAxis(x,-15*radians),RotateAroundAxis(forward,160*radians));
    const auto wrist = bones[8];
    auto target = Concat(rotation,wrist);
    for (int r=0;r<3;++r) target[r][3]=wrist[r][3];
    for (int i=0;i<24;++i) bones[i]=Reanchor(bones[i],wrist,target);
    // Use anatomical joint positions, not a hardcoded bone-roll convention.
    Vector from(wrist[0][3]-bones[7][0][3],wrist[1][3]-bones[7][1][3],wrist[2][3]-bones[7][2][3]);
    const float length = sqrtf(from.LengthSqr());
    if (length<=1e-6f) return;
    from*=1.0f/length;
    const Vector to=up*sinf(35*radians)+forward*cosf(35*radians);
    const Vector axis(from.y*to.z-from.z*to.y,from.z*to.x-from.x*to.z,from.x*to.y-from.y*to.x);
    const float angle=atan2f(sqrtf(axis.LengthSqr()),from.x*to.x+from.y*to.y+from.z*to.z);
    auto source=bones[7];for (int r=0;r<3;++r) source[r][3]=wrist[r][3];
    target=Concat(RotateAroundAxis(axis,angle),source);
    for (int r=0;r<3;++r) target[r][3]=wrist[r][3];
    for (int i=0;i<8;++i) bones[i]=Reanchor(bones[i],source,target);
}

inline void ApplyGunGrip(const matrix3x4_t *bind, matrix3x4_t *result,
    const float *curl)
{
    // Fold the distal joints back into the rear housing. The independently
    // tracked bare hand keeps its own open-hand curl profile.
    const float restingGrip[5] = {0.55f, 0.65f, 0.80f, 0.80f, 0.80f};
    const float squeezedGrip[5] = {0.80f, 0.85f, 0.90f, 0.90f, 0.90f};
    float grip[5];
    for (int i = 0; i < 5; ++i) {
        const float input = std::isfinite(curl[i])
            ? fmaxf(0.0f, fminf(1.0f, curl[i])) : 0.0f;
        grip[i] = restingGrip[i] + (squeezedGrip[i] - restingGrip[i]) * input;
    }
    const float enclosedGripFlexion[3] = {0.50f, 1.20f, 1.20f};
    ApplyFingerCurlChain(bind, result, grip, 0, 8, false, enclosedGripFlexion);
    SeatGunHand(result);
}

inline void StraightenGunWrist(matrix3x4_t *bones) {
    // The stock first-person pose bends the wrist about 50 degrees. Keep the
    // hand and gun fixed and rotate the forearm chain around the wrist joint.
    const auto hand = bones[8];
    auto forearmAtWrist = bones[7];
    for (int row = 0; row < 3; ++row) forearmAtWrist[row][3] = hand[row][3];
    matrix3x4_t neutral;
    for (int row = 0; row < 3; ++row) {
        neutral[row][0] = hand[row][0];
        neutral[row][1] = hand[row][2];
        neutral[row][2] = -hand[row][1];
        neutral[row][3] = hand[row][3];
    }
    for (int i = 0; i < 8; ++i) bones[i] = Reanchor(bones[i], forearmAtWrist, neutral);
}
}
