$modelname "corehub_intro/transport_ring_ng.mdl"
$origin 0 0 0 -90
$body body "transport_ring.smd"
$cdmaterials "models/corehub_intro"
$surfaceprop "metal"
$staticprop
$renamematerial "tube_glass" "tube_glass_none"
$texturegroup skinfamilies
{
{ "tube_d0" "tube_d1" "tube_d2" "tube_d3" "tube_dh0" "tube_dh1" "tube_dh2" "tube_dh3" "tube_dlip" }
{ "tube_m0" "tube_m1" "tube_m2" "tube_m3" "tube_mh0" "tube_mh1" "tube_mh2" "tube_mh3" "tube_mlip" }
{ "tube_b0" "tube_b1" "tube_b2" "tube_b3" "tube_bh0" "tube_bh1" "tube_bh2" "tube_bh3" "tube_blip" }
}
$sequence idle "transport_ring.smd" fps 1
