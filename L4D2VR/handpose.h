#pragma once
#include "sdk/vector.h"
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

// The Source controller basis is left-handed (AngleVectors' right axis is
// negated).  The hand mesh uses +X along the fingers, +Z toward the back of
// the hand, and must remain a proper rigid frame for correct skin lighting.
// Mirror the lateral axis for the left hand while keeping each palm aligned
// with its own controller instead of turning both hands into edge-on chops.
inline matrix3x4_t ControllerHandFrame(const Vector& forward, const Vector& right,
    const Vector& up, const Vector& position, bool left)
{
    return Frame(forward, left ? -right : right, left ? up : -up, position);
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

inline matrix3x4_t FingerBend(float radians)
{
    // The custom VPK finger bones run down local +X.  Local +Z is the back of
    // the hand, so the knuckle hinge is local Y: rotating around Z only turns
    // the fingers sideways and produces the user's karate-chop pose.  Positive
    // Y rotation sends +X toward the palm (-Z); the mirrored wrist frame makes
    // the same local pose correct for both hands.
    const float c = cosf(radians), s = sinf(radians);
    return Frame({c,0,-s}, {0,1,0}, {s,0,c}, {0,0,0});
}

inline void ApplyFingerCurlChain(const matrix3x4_t *bind, matrix3x4_t *result,
    const float *curl, int offset, int wrist)
{
    // Valve's hand skeleton uses thumb, index, middle, ring, pinky chains.
    // Each chain has three bones in the custom VPK model.  Curling the local
    // parent-to-child frame bends the mesh while preserving its authored UVs.
    static const int chains[5][3] = {
        {21,22,23}, {18,19,20}, {15,16,17}, {12,13,14}, {9,10,11}
    };
    // Distribute the tracked curl down the three segments. Applying the same
    // angle at every joint folds the custom mesh into a thick stack of lobes;
    // a real finger bends most at the knuckle and progressively less toward
    // the fingertip.
    static const float segmentWeight[3] = {0.55f, 0.30f, 0.15f};
    for (int finger = 0; finger < 5; ++finger) {
        // Both authored hand chains use the same local curl sign; their
        // mirrored wrist frames already account for left/right orientation.
        // The Pico compatibility layer reports a normalized curl value, while
        // this model's authored bind pose is almost fully open.  The previous
        // small multiplier only moved each joint a few degrees, which read as
        // four rigid, parallel fingers.  Use a useful range for the full
        // 0..1 input and let the segment weights keep the knuckle dominant.
        const float totalCurl = curl[finger] * (finger == 0 ? 0.78f : 1.05f);
        int parent = wrist;
        for (int segment = 0; segment < 3; ++segment) {
            const int bone = chains[finger][segment] + offset;
            const auto local = Concat(InverseRigid(bind[parent]), bind[bone]);
            // Source's viewmodel matrices use the parent-frame convention:
            // pre-multiplying rotates the segment and advances the next joint
            // along that rotated segment. Keep the per-segment weights small
            // enough that the authored mesh remains fully visible.
            result[bone] = Concat(result[parent], Concat(FingerBend(totalCurl * segmentWeight[segment]), local));
            parent = bone;
        }
    }
}

inline void ApplyFingerCurl(const matrix3x4_t *bind, matrix3x4_t *result,
    const float *leftCurl, const float *rightCurl)
{
    ApplyFingerCurlChain(bind, result, leftCurl, 0, 8);
    ApplyFingerCurlChain(bind, result, rightCurl, 19, 27);
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
