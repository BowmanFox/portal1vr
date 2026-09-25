// Created by Crowbar 0.68

$modelname "weapons/V_hands.mdl"

$body "BowmanHands" "bowman_view.smd"


$surfaceprop "default"

$contents "solid"

$illumposition 1.105 -21.215 -15.439

$cdmaterials "models\Weapons\v_models\V_hands\"



$cbox 0 0 0 0 0 0

$bbox 5.796 -17.333 -31.962 36.635 19.542 1.084



$sequence "admire" {
	"v_hands_anims\admire.smd"
	activity "ACT_VM_IDLE" 1
	fadein 0.2
	fadeout 0.2
	fps 30
}
$cdmaterials "models/bowman_corehub"

$sequence "bowman_proportion_basis" "proportion_basis.smd" fps 1 hidden
$animation "a_bowman_proportions" "proportion_target.smd" subtract "bowman_proportion_basis" 0
$sequence "bowman_proportions" "a_bowman_proportions" predelta autoplay hidden
$definebone "ValveBiped.Bip01" "" -0.130918503 -2.493414879 36.895614624 -0.000000000 0.000000000 89.999982014 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_Spine" "ValveBiped.Bip01" 0.000000000 3.345131159 -2.981897831 4.766608022 89.999982014 89.999988844 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_Spine1" "ValveBiped.Bip01_Spine" 3.995837927 0.000000919 0.000000113 0.000000504 -1.650977211 0.000000376 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_Spine2" "ValveBiped.Bip01_Spine1" 3.520300388 -0.000002718 0.000000128 -0.000026283 5.575223019 -0.000000199 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_Spine4" "ValveBiped.Bip01_Spine2" 8.921475410 0.000000504 -0.000003772 0.000021264 10.680679286 0.000004301 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Clavicle" "ValveBiped.Bip01_Spine4" 4.834897518 -1.604231596 3.873075724 -57.174246542 177.835804929 -32.099956156 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_UpperArm" "ValveBiped.Bip01_L_Clavicle" 5.219933987 -0.148934245 -3.088737488 25.888773370 -0.419972964 -177.869832931 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Forearm" "ValveBiped.Bip01_L_UpperArm" 9.383000374 -0.000008583 0.000009812 21.208300863 -3.263952957 -103.225209002 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Hand" "ValveBiped.Bip01_L_Forearm" 9.324225426 -0.219392046 -0.009091601 3.866744686 -9.623792036 35.964897245 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Finger4" "ValveBiped.Bip01_L_Hand" 4.594272614 -2.634877443 1.198446035 -161.433693033 -69.702831801 -14.981476944 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Finger41" "ValveBiped.Bip01_L_Finger4" 0.000005692 1.611065984 -0.000000596 -1.926463393 -1.529472842 -3.222124025 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Finger42" "ValveBiped.Bip01_L_Finger41" 0.000004679 1.348497987 0.000000477 -0.288246283 -4.465572984 -4.561021889 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Finger3" "ValveBiped.Bip01_L_Hand" 3.523627043 -0.928595245 0.246670783 -144.158382434 -74.832249226 -12.217961916 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Finger31" "ValveBiped.Bip01_L_Finger3" -0.000001475 2.304782629 -0.000000760 -0.973659688 -4.374850142 -1.057504422 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Finger32" "ValveBiped.Bip01_L_Finger31" 0.000002801 2.038694620 0.000002563 -0.223856195 -12.445282564 -4.863843449 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Finger2" "ValveBiped.Bip01_L_Hand" 3.150727510 -0.000002998 0.000003397 -144.743593042 -73.712610466 0.843178369 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Finger21" "ValveBiped.Bip01_L_Finger2" -0.000004709 2.462731361 -0.000010461 -0.492986032 -7.589887206 -8.551165468 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Finger22" "ValveBiped.Bip01_L_Finger21" -0.000006385 1.798555732 0.000002444 0.897161996 -2.503480976 -4.692217870 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Finger1" "ValveBiped.Bip01_L_Hand" 2.624195814 1.354360700 -0.300923347 -135.444823242 -79.836544416 7.117941198 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Finger11" "ValveBiped.Bip01_L_Finger1" -0.000005305 2.140417576 -0.000002563 0.445014359 -6.520448202 -5.531492305 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Finger12" "ValveBiped.Bip01_L_Finger11" 0.000002325 1.462279677 0.000000179 3.757210650 -6.838195432 -9.525609774 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Finger0" "ValveBiped.Bip01_L_Hand" -1.046082377 2.404732466 0.000001311 -77.931713939 -27.504251420 -33.784970654 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Finger01" "ValveBiped.Bip01_L_Finger0" 0.000007868 2.659261942 0.000003308 3.545093575 -5.122025880 5.760186249 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_L_Finger02" "ValveBiped.Bip01_L_Finger01" 0.000007749 1.780092597 -0.000008062 -8.091403237 5.725906383 -15.490515575 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Clavicle" "ValveBiped.Bip01_Spine4" 4.834960938 -1.604258180 -3.873142481 57.174068957 177.835763948 32.099925420 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_UpperArm" "ValveBiped.Bip01_R_Clavicle" 5.219931126 -0.148937821 3.088741064 -25.888937294 -0.419902875 177.869778290 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Forearm" "ValveBiped.Bip01_R_UpperArm" 9.382997513 0.000000924 0.000016056 -21.208488694 -3.263953171 103.225243153 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Hand" "ValveBiped.Bip01_R_Forearm" 9.324227333 -0.219396874 0.009088278 -3.866721634 -9.623827041 -35.964900660 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger4" "ValveBiped.Bip01_R_Hand" 4.594276905 -2.634880304 -1.198447704 161.433734015 -69.702838631 14.981495727 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger41" "ValveBiped.Bip01_R_Finger4" 0.000009149 1.611065030 0.000005603 1.926443970 -1.529477217 3.222114207 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger42" "ValveBiped.Bip01_R_Finger41" 0.000005662 1.348500133 -0.000003457 0.288222831 -4.465586644 4.561015059 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger3" "ValveBiped.Bip01_R_Hand" 3.523628950 -0.928599834 -0.246675402 144.158450736 -74.832290207 12.217966184 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger31" "ValveBiped.Bip01_R_Finger3" -0.000001356 2.304786444 -0.000002354 0.973532369 -4.374922286 1.057467603 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger32" "ValveBiped.Bip01_R_Finger31" -0.000003606 2.038699865 -0.000005603 0.223908702 -12.445224507 4.863851132 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger2" "ValveBiped.Bip01_R_Hand" 3.150730133 -0.000010108 -0.000007600 144.743675004 -73.712651447 -0.843162040 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger21" "ValveBiped.Bip01_R_Finger2" 0.000001758 2.462725163 0.000003427 0.492878990 -7.589941847 8.551131317 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger22" "ValveBiped.Bip01_R_Finger21" -0.000012338 1.798557162 0.000003040 -0.897111944 -2.503447892 4.692235373 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger1" "ValveBiped.Bip01_R_Hand" 2.624198437 1.354355931 0.300919324 135.444891543 -79.836592227 -7.117918573 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger11" "ValveBiped.Bip01_R_Finger1" -0.000004709 2.140412807 0.000003695 -0.445030207 -6.520455886 5.531484622 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger12" "ValveBiped.Bip01_R_Finger11" 0.000005186 1.462273479 -0.000004828 -3.757230286 -6.838203970 9.525606359 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger0" "ValveBiped.Bip01_R_Hand" -1.046080470 2.404729843 -0.000004530 77.931768581 -27.504148967 33.785107258 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger01" "ValveBiped.Bip01_R_Finger0" 0.000008702 2.659259558 -0.000014603 -3.545084611 -5.122029295 -5.760173015 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger02" "ValveBiped.Bip01_R_Finger01" 0.000002146 1.780092120 0.000009432 8.091357133 5.725910652 15.490471179 0 0 0 0 0 0
