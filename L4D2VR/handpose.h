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
    for (int i = 5; i < 24; ++i) result[i] = Reanchor(bones[i], bones[8], leftTarget);
    for (int i = 24; i < 43; ++i) result[i] = Reanchor(bones[i], bones[27], rightTarget);
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
