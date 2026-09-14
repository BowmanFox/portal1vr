#pragma once

#include "handpose.h"

namespace FirstPersonBody
{
inline constexpr int MaxBones = 128;

inline bool LookingDown(float pitch)
{
    return std::isfinite(pitch) && pitch >= 30.0f && pitch <= 90.0f;
}

inline Vector HorizontalCameraOffset(const Vector &modelEyes, const Vector &camera)
{
    return {camera.x - modelEyes.x, camera.y - modelEyes.y, 0};
}

inline bool IsDescendant(const int *parents, int count, int bone, int ancestor)
{
    if (!parents || count <= 0 || bone < 0 || bone >= count || ancestor < 0 || ancestor >= count)
        return false;

    for (int current = bone, steps = 0; current >= 0 && current < count && steps <= count; current = parents[current], ++steps)
    {
        if (current == ancestor)
            return true;
    }

    return false;
}

inline bool IsDescendantOfAny(const int *parents, int count, int bone,
    const int *ancestors, int ancestorCount)
{
    if (!ancestors || ancestorCount <= 0)
        return false;

    for (int i = 0; i < ancestorCount; ++i)
        if (IsDescendant(parents, count, bone, ancestors[i]))
            return true;

    return false;
}

inline void CollapseBranches(matrix3x4_t *bones, const int *parents, int count,
    const int *hiddenRoots, int hiddenRootCount, int hips, const Vector &pivot)
{
    if (!bones || !parents || !hiddenRoots || count <= 0 || count > MaxBones
        || hiddenRootCount <= 0 || hiddenRootCount > MaxBones
        || hips < 0 || hips >= count)
        return;

    const matrix3x4_t collapsed = HandPose::Frame(
        {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, pivot);
    for (int i = 0; i < count; ++i)
    {
        if (IsDescendantOfAny(parents, count, i, hiddenRoots, hiddenRootCount))
            bones[i] = collapsed;
    }
}

// Collapse only the upper-body branch in a temporary bone palette.  A zero
// rotation is intentional: vertices weighted to the upper branch become
// degenerate at the hip pivot instead of stretching a long strip from the
// pelvis toward a hidden point behind the camera.  The source model and its
// cached animation matrices are never changed.
inline void CollapseUpperBody(matrix3x4_t *bones, const int *parents, int count,
    int upperRoot, int hips, const Vector &pivot)
{
    CollapseBranches(bones, parents, count, &upperRoot, 1, hips, pivot);
}

// Each hidden branch closes at its own attachment. Collapsing a head or arm
// at the pelvis pulls vertices with mixed weights into long torso triangles.
inline void CollapseBranchesAtRoots(matrix3x4_t *bones, const int *parents,
    int count, const int *roots, int rootCount)
{
    if (!bones || !parents || !roots || count <= 0 || count > MaxBones
        || rootCount < 0 || rootCount > MaxBones) return;
    for (int r = 0; r < rootCount; ++r) {
        const int root = roots[r];
        if (root < 0 || root >= count) continue;
        const Vector pivot(bones[root][0][3], bones[root][1][3], bones[root][2][3]);
        CollapseBranches(bones, parents, count, &root, 1, root, pivot);
    }
}
}
