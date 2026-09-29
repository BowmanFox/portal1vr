// Created by Crowbar 0.68

$modelname "weapons/v_portalgun.mdl"

$body "BowmanHands" "bowman_view.smd"


$surfaceprop "default"

$contents "solid"

$illumposition -5.757 -17.474 -5.546

$cdmaterials "models\Weapons\v_models\v_portalgun\"



$attachment "muzzle" "ValveBiped.Front_Cover" 0 2.2 2.8 rotate -90 0 0
$attachment "Arm1_attach1" "ValveBiped.Arm1_A" 0 0 0 rotate 0 0 0
$attachment "Arm1_attach2" "ValveBiped.Arm1_B" 0 0.2 -0.1 rotate 0 0 0
$attachment "Arm1_attach3" "ValveBiped.Arm1_C" -1.25 0.1 1.06 rotate 0 0 0
$attachment "Arm2_attach1" "ValveBiped.Arm2_A" 0 0 0 rotate 0 0 0
$attachment "Arm2_attach2" "ValveBiped.Arm2_B" 0 0.2 -0.1 rotate 0 0 0
$attachment "Arm2_attach3" "ValveBiped.Arm2_C" 0.1 -1.25 1 rotate 0 0 0
$attachment "Arm3_attach1" "ValveBiped.Arm3_A" 0 0 -0.3 rotate 0 0 0
$attachment "Arm3_attach2" "ValveBiped.Arm3_B" -0.1 0.3 -0.1 rotate 0 0 0
$attachment "Arm3_attach3" "ValveBiped.Arm3_C" -0.1 -1.25 1.05 rotate 0 0 0
$attachment "Body_light" "ValveBiped.Base" 0.25 5.45 10.5 rotate 0 0 0
$attachment "Beam_point1" "ValveBiped.Front_Cover" 0.01 2.4 -3.1 rotate 0 0 0
$attachment "Beam_point2" "ValveBiped.Front_Cover" -0.01 2.39 -3.4 rotate 0 0 0
$attachment "Beam_point3" "ValveBiped.Front_Cover" -0.02 2.37 -3.7 rotate 0 0 0
$attachment "Beam_point4" "ValveBiped.Front_Cover" -0.04 2.36 -4 rotate 0 0 0
$attachment "Beam_point5" "ValveBiped.Front_Cover" -0.05 2.35 -4.3 rotate 0 0 0
$attachment "Inside_effects" "ValveBiped.Front_Cover" 0 2.2 0 rotate 0 0 0

$cbox 0 0 0 0 0 0

$bbox -2.432 -12.519 -16.433 37.381 1.005 5.342



$sequence "idle" {
	"v_portalgun_anims\idle.smd"
	activity "ACT_VM_IDLE" 1
	fadein 0.2
	fadeout 0.2
	node "Ready"
	fps 30
	loop
}

$sequence "fire1" {
	"v_portalgun_anims\fire1.smd"
	activity "ACT_VM_PRIMARYATTACK" 1
	{ event AE_MUZZLEFLASH 0 "COMBINE MUZZLE" }
	fadein 0.2
	fadeout 0.2
	node "Fire"
	snap
	fps 30
}

$sequence "fizzle" {
	"v_portalgun_anims\fizzle.smd"
	activity "ACT_VM_FIZZLE" 1
	fadein 0.2
	fadeout 0.2
	node "Ready"
	snap
	fps 30
}

$sequence "draw" {
	"v_portalgun_anims\draw.smd"
	activity "ACT_VM_DRAW" 1
	fadein 0.2
	fadeout 0.2
	node "Ready"
	snap
	fps 30
}

$sequence "holster" {
	"v_portalgun_anims\holster.smd"
	activity "ACT_VM_HOLSTER" 1
	fadein 0.2
	fadeout 0.2
	node "Ready"
	fps 30
}

$sequence "idletolow" {
	"v_portalgun_anims\idletolow.smd"
	activity "ACT_VM_LOWERED_TO_IDLE" 1
	fadein 0.2
	fadeout 0.2
	transition "Ready" "Low"
	fps 30
}

$sequence "lowtoidle" {
	"v_portalgun_anims\lowtoidle.smd"
	activity "ACT_VM_IDLE_TO_LOWERED" 1
	fadein 0.2
	fadeout 0.2
	transition "Low" "Ready"
	fps 30
}

$sequence "lowidle" {
	"v_portalgun_anims\lowidle.smd"
	activity "ACT_VM_IDLE_LOWERED" 1
	fadein 0.2
	fadeout 0.2
	node "Low"
	fps 30
	loop
}

$sequence "pickup" {
	"v_portalgun_anims\pickup.smd"
	activity "ACT_VM_PICKUP" 1
	fadein 0.2
	fadeout 0.2
	node "Fire"
	fps 30
}

$sequence "release" {
	"v_portalgun_anims\release.smd"
	activity "ACT_VM_RELEASE" 1
	fadein 0.2
	fadeout 0.2
	node "Fire"
	fps 30
}
$cdmaterials "models/bowman_corehub"

$sequence "bowman_proportion_basis" "proportion_basis.smd" fps 1 hidden
$animation "a_bowman_proportions" "proportion_target.smd" subtract "bowman_proportion_basis" 0
$sequence "bowman_proportions" "a_bowman_proportions" predelta autoplay hidden
$definebone "ValveBiped.Bip01" "" -20.199989319 -9.103698730 -12.653491974 118.508399308 -51.659206882 36.603967309 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_Spine" "ValveBiped.Bip01" 0.000000238 3.345131636 -2.981899738 4.766614852 90.000098127 89.999961523 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_Spine1" "ValveBiped.Bip01_Spine" 3.995842695 0.000002861 0.000006437 -0.000105014 -1.651037189 -0.000000107 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_Spine2" "ValveBiped.Bip01_Spine1" 3.520301819 -0.000000298 0.000000954 -0.000016862 5.575284917 0.000000960 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_Spine4" "ValveBiped.Bip01_Spine2" 8.921482086 0.000000745 -0.000002742 0.556569277 -23.972821638 -2.044498454 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Clavicle" "ValveBiped.Bip01_Spine4" -0.226196796 -19.477071762 -5.292819500 24.993217749 123.942812000 21.201597033 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_UpperArm" "ValveBiped.Bip01_R_Clavicle" 5.219935894 -0.148940772 3.088733673 -25.888920219 -0.419971310 177.869819271 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Forearm" "ValveBiped.Bip01_R_UpperArm" 9.383004189 0.000002585 0.000020839 -21.208437467 -3.263956799 103.225311455 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Hand" "ValveBiped.Bip01_R_Forearm" 9.324231148 -0.219384819 0.009085774 -3.866816403 -9.623926932 -35.964962131 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger4" "ValveBiped.Bip01_R_Hand" 4.594279289 -2.634861469 -1.198447227 161.433679373 -69.702640555 14.981459869 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger41" "ValveBiped.Bip01_R_Finger4" 0.000010252 1.611064792 0.000001192 1.926436713 -1.529512435 3.222126800 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger42" "ValveBiped.Bip01_R_Finger41" -0.000000954 1.348503113 -0.000001431 0.288331900 -4.465528587 4.561004814 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger3" "ValveBiped.Bip01_R_Hand" 3.523628712 -0.928584814 -0.246673822 144.158628320 -74.832153603 12.217891052 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger31" "ValveBiped.Bip01_R_Finger3" -0.000003994 2.304785252 0.000000477 0.973477941 -4.374897100 1.057504956 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger32" "ValveBiped.Bip01_R_Finger31" 0.000000000 2.038698673 -0.000002861 0.223902486 -12.445240729 4.863866927 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger2" "ValveBiped.Bip01_R_Hand" 3.150727749 0.000005722 -0.000005603 144.742595834 -73.712439712 -0.843216842 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger21" "ValveBiped.Bip01_R_Finger2" -0.000001073 2.462730169 0.000001907 0.493869688 -7.589940993 8.551013496 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger22" "ValveBiped.Bip01_R_Finger21" -0.000010490 1.798557043 -0.000003934 -0.896974806 -2.503435086 4.692219578 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger1" "ValveBiped.Bip01_R_Hand" 2.624195576 1.354366064 0.300923467 135.444932525 -79.836441963 -7.117979191 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger11" "ValveBiped.Bip01_R_Finger1" -0.000000536 2.140414238 0.000003815 -0.444777170 -6.520473815 5.531480780 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger12" "ValveBiped.Bip01_R_Finger11" 0.000000358 1.462278843 -0.000001967 -3.757515020 -6.838159147 9.525658439 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger0" "ValveBiped.Bip01_R_Hand" -1.046089649 2.404725075 -0.000001729 77.931775411 -27.503641825 33.785397541 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger01" "ValveBiped.Bip01_R_Finger0" 0.000012584 2.659263134 -0.000007391 -3.545115560 -5.122030576 -5.760166185 0 0 0 0 0 0
$definebone "ValveBiped.Bip01_R_Finger02" "ValveBiped.Bip01_R_Finger01" 0.000004113 1.780091763 0.000006676 8.091235044 5.725855157 15.490478009 0 0 0 0 0 0
$definebone "ValveBiped.Base" "ValveBiped.Bip01_R_Hand" -0.280542731 -0.043848991 0.112660527 109.227353848 -65.816843484 -64.105000002 0 0 0 0 0 0
$definebone "ValveBiped.Front_Cover" "ValveBiped.Base" -0.000002980 0.000002980 22.656490326 -0.000007577 -0.000013714 0.000054628 0 0 0 0 0 0
$definebone "ValveBiped.Front_Cover_Stop" "ValveBiped.Front_Cover" 0.000001431 -0.000008404 -9.245958328 0.000001067 -0.000000854 -0.000026760 0 0 0 0 0 0
$definebone "ValveBiped.Arm1_A" "ValveBiped.Front_Cover" -1.576426744 4.638202190 0.069090903 -1.521621966 34.263247820 1.231270091 0 0 0 0 0 0
$definebone "ValveBiped.Arm1_B" "ValveBiped.Arm1_A" 0.022695541 2.517579556 2.098716021 -0.000000213 0.000006617 0.000000000 0 0 0 0 0 0
$definebone "ValveBiped.Arm1_C" "ValveBiped.Arm1_B" 0.054254055 0.579428673 4.187383175 -0.000027001 89.999913712 0.000013554 0 0 0 0 0 0
$definebone "ValveBiped.Arm2_A" "ValveBiped.Front_Cover" 3.599335670 0.093094677 -0.024611831 1.972918498 -119.304170987 -0.489363257 0 0 0 0 0 0
$definebone "ValveBiped.Arm2_B" "ValveBiped.Arm2_A" -0.035751343 2.512600660 2.098586798 -0.000001014 0.000000640 0.000001067 0 0 0 0 0 0
$definebone "ValveBiped.Arm2_C" "ValveBiped.Arm2_B" -0.071235597 0.559594512 4.226671696 -0.000006136 -0.000000213 0.000001067 0 0 0 0 0 0
$definebone "ValveBiped.Arm3_A" "ValveBiped.Front_Cover" -3.282006502 -0.134423792 -0.097992063 0.000048825 123.218675344 0.000058590 0 0 0 0 0 0
$definebone "ValveBiped.Arm3_B" "ValveBiped.Arm3_A" 0.036786199 2.570756674 2.023870945 -0.000003362 0.000008965 0.000007684 0 0 0 0 0 0
$definebone "ValveBiped.Arm3_C" "ValveBiped.Arm3_B" -0.103077292 0.682138681 4.218961239 -0.000000213 -0.000000213 -0.000013554 0 0 0 0 0 0
$definebone "ValveBiped.Wire1_A" "ValveBiped.Front_Cover" -1.850000262 4.368043423 -7.061016083 -1.521679276 34.263247820 1.231385350 0 0 0 0 0 0
$definebone "ValveBiped.Wire1_B" "ValveBiped.Front_Cover" -1.931276083 5.316288471 -4.070713520 1.031585775 32.220549976 -38.661356891 0 0 0 0 0 0
$definebone "ValveBiped.Wire1_C" "ValveBiped.Front_Cover" -2.754201651 6.422506809 -1.363417864 -1.521696565 34.263234160 28.281890655 0 0 0 0 0 0
$definebone "ValveBiped.Wire2_A" "ValveBiped.Front_Cover" 3.602583885 0.858876824 -7.121089458 1.972914016 -119.304198308 -0.489433480 0 0 0 0 0 0
$definebone "ValveBiped.Wire2_B" "ValveBiped.Front_Cover" 4.197438240 -0.046528190 -4.251001358 7.574764313 -123.504928572 -36.968699411 0 0 0 0 0 0
$definebone "ValveBiped.Wire2_C" "ValveBiped.Front_Cover" 5.318143845 -0.817591965 -1.521418810 1.972910174 -119.304170987 23.363367273 0 0 0 0 0 0
$definebone "ValveBiped.Wire3_A" "ValveBiped.Front_Cover" -3.331625462 0.672283769 -7.197002411 0.000050319 123.218689005 0.000040554 0 0 0 0 0 0
$definebone "ValveBiped.Wire3_B" "ValveBiped.Front_Cover" -3.776882648 -0.322165966 -4.363084793 -5.326453442 127.807128127 -40.844500501 0 0 0 0 0 0
$definebone "ValveBiped.Wire3_C" "ValveBiped.Front_Cover" -4.896676064 -1.171614766 -1.564593315 0.000065687 123.218689005 28.153423334 0 0 0 0 0 0
