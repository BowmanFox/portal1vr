$modelname "player.mdl"
$upaxis Y
$model "Bowman" "bowman_body.smd"
$model "Bowman details" "bowman_details.smd" {
 eyeball "righteye" "bip_head" -2.5850699 63.7276001 1.7326936 "eye_r" 4.2939110 0 "iris_unused" 9.5000000
 eyeball "lefteye" "bip_head" 2.5850699 63.7276001 1.7326936 "eye_l" 4.2939110 0 "iris_unused" 9.5000000
 flexcontroller eyes range -25 25 "eyes_updown"
 flexcontroller eyes range -30 30 "eyes_rightleft"
}
$surfaceprop flesh
$contents solid
$cdmaterials "models/bowman_corehub"
$mostlyopaque
$ambientboost
$bbox -24 -30 0 24 30 78
$eyeposition 0 -1.7326936 63.7276001
$definebone "bip_pelvis" "" 0.000000000 30.915294647 -1.393723726 -0.000000000 0.000000000 -178.278674395 0 0 0 0 0 0
$definebone "bip_spine_0" "bip_pelvis" 0.000000000 -7.718697548 -1.967558026 -0.000000000 0.000000000 -0.803436113 0 0 0 0 0 0
$definebone "bip_spine_1" "bip_spine_0" 0.000000000 -3.783939123 0.162977859 -0.000000000 0.000000000 -3.463432261 0 0 0 0 0 0
$definebone "bip_spine_2" "bip_spine_1" 0.000000000 -2.800630569 0.686419368 -0.000000000 0.000000000 -10.034670603 0 0 0 0 0 0
$definebone "bip_spine_3" "bip_spine_2" 0.000000000 -2.877394915 0.187924087 -0.000000000 0.000000000 9.048801098 0 0 0 0 0 0
$definebone "bip_collar_R" "bip_spine_3" -0.618524432 -3.756993771 -2.310322285 -6.563979986 87.704799396 13.802431761 0 0 0 0 0 0
$definebone "bip_upperArm_R" "bip_collar_R" -0.000004772 6.067139626 0.000004709 4.642724612 91.349026337 -169.494299801 0 0 0 0 0 0
$definebone "bip_lowerArm_R" "bip_upperArm_R" 9.383005142 0.000005811 -0.000001550 -20.096737095 0.255639200 -75.076974904 0 0 0 0 0 0
$definebone "bip_hand_R" "bip_lowerArm_R" 9.326812744 -0.000000071 0.000014877 -94.240341036 23.437981967 82.548225139 0 0 0 0 0 0
$definebone "bip_twistArm_R" "bip_lowerArm_R" 4.663411617 -0.000000656 0.000007480 -132.572537450 5.472050877 95.472746218 0 0 0 0 0 0
$definebone "bip_pinky_0_R" "bip_hand_R" -1.909900784 -4.692540169 -1.954120398 -77.203274264 153.795519805 38.415350553 0 0 0 0 0 0
$definebone "bip_pinky_1_R" "bip_pinky_0_R" -0.000039279 1.611063719 0.000072241 2.750295838 3.038941767 2.119147512 0 0 0 0 0 0
$definebone "bip_pinky_2_R" "bip_pinky_1_R" 0.000071883 1.348505139 -0.000110149 -8.111016125 27.925016686 32.956366255 0 0 0 0 0 0
$definebone "bip_ring_0_R" "bip_hand_R" -1.100126982 -3.471724749 -0.275598049 -79.677605914 143.734801422 39.780770255 0 0 0 0 0 0
$definebone "bip_ring_1_R" "bip_ring_0_R" -0.000035727 2.304784536 0.000063658 0.771413731 1.403274745 4.316076791 0 0 0 0 0 0
$definebone "bip_ring_2_R" "bip_ring_1_R" 0.000016481 2.038696527 0.000002354 -4.344946720 14.210741323 32.906943006 0 0 0 0 0 0
$definebone "bip_middle_0_R" "bip_hand_R" -0.515994787 -3.071914911 0.473482013 -69.245632598 105.063854945 78.639731349 0 0 0 0 0 0
$definebone "bip_middle_1_R" "bip_middle_0_R" -0.000071049 2.462727308 0.000150293 -0.994777459 8.428400502 7.658595494 0 0 0 0 0 0
$definebone "bip_middle_2_R" "bip_middle_1_R" -0.000001192 1.798555374 -0.000030398 -3.198701385 11.628819680 30.029117931 0 0 0 0 0 0
$definebone "bip_index_0_R" "bip_hand_R" 0.371694744 -2.518731594 1.526139021 -67.400866805 87.837598764 90.670747572 0 0 0 0 0 0
$definebone "bip_index_1_R" "bip_index_0_R" -0.000035167 2.140416145 0.000068367 -0.934834118 5.791557308 6.159163211 0 0 0 0 0 0
$definebone "bip_index_2_R" "bip_index_1_R" 0.000027180 1.462277770 -0.000089049 -2.464105362 5.190827229 47.841042343 0 0 0 0 0 0
$definebone "bip_thumb_0_R" "bip_hand_R" 1.944491863 0.972336411 1.466470003 -19.374403609 22.736967209 144.907517582 0 0 0 0 0 0
$definebone "bip_thumb_1_R" "bip_thumb_0_R" 0.000020742 2.659258127 0.000113249 -3.970439337 -6.531833274 4.997853894 0 0 0 0 0 0
$definebone "bip_thumb_2_R" "bip_thumb_1_R" -0.000030041 1.780094385 -0.000014544 -3.420792243 -36.743146074 -24.781157450 0 0 0 0 0 0
$definebone "bip_collar_L" "bip_spine_3" 0.618524432 -3.756993771 -2.310322285 6.563988097 -87.704854038 -166.197531413 0 0 0 0 0 0
$definebone "bip_upperArm_L" "bip_collar_L" -0.000001290 -6.067140102 -0.000000477 -4.642762605 -88.651060634 79.494331448 0 0 0 0 0 0
$definebone "bip_lowerArm_L" "bip_upperArm_L" 9.383004189 -0.000000834 0.000003651 -0.240027628 20.096942001 -15.010829682 0 0 0 0 0 0
$definebone "bip_hand_L" "bip_lowerArm_L" 9.326812744 -0.000003252 0.000011621 85.760838766 -23.442098864 -97.456219493 0 0 0 0 0 0
$definebone "bip_twistArm_L" "bip_lowerArm_L" 4.663411140 -0.000003159 0.000004023 47.427713446 -5.472389398 -84.527504677 0 0 0 0 0 0
$definebone "bip_thumb_0_L" "bip_hand_L" -1.944480896 0.972367764 1.466472864 19.375008081 -22.739014558 -35.090038804 0 0 0 0 0 0
$definebone "bip_thumb_1_L" "bip_thumb_0_L" 0.000004530 -2.659265041 0.000000954 -3.971948809 -6.530070658 4.995367279 0 0 0 0 0 0
$definebone "bip_thumb_2_L" "bip_thumb_1_L" -0.000001192 -1.780093193 0.000006437 -3.420514767 -36.744071565 -24.781135252 0 0 0 0 0 0
$definebone "bip_index_0_L" "bip_hand_L" -0.371761143 -2.518736601 1.526120901 67.402109900 -87.839313142 -89.327761626 0 0 0 0 0 0
$definebone "bip_index_1_L" "bip_index_0_L" -0.000001192 -2.140412569 -0.000006557 -0.934962077 5.789645708 6.154266393 0 0 0 0 0 0
$definebone "bip_index_2_L" "bip_index_1_L" 0.000004053 -1.462278128 0.000012815 -2.464082524 5.191859441 47.843975909 0 0 0 0 0 0
$definebone "bip_middle_0_L" "bip_hand_L" 0.515921652 -3.071930170 0.473463297 110.752330184 74.934025875 78.642422443 0 0 0 0 0 0
$definebone "bip_middle_1_L" "bip_middle_0_L" 0.000000775 -2.462728024 -0.000006616 -0.993953461 8.426883346 7.654110621 0 0 0 0 0 0
$definebone "bip_middle_2_L" "bip_middle_1_L" 0.000002980 -1.798555136 0.000003219 -3.198995297 11.628769307 30.029575554 0 0 0 0 0 0
$definebone "bip_ring_0_L" "bip_hand_L" 1.100046396 -3.471746445 -0.275618553 100.321668265 36.257581096 39.776245254 0 0 0 0 0 0
$definebone "bip_ring_1_L" "bip_ring_0_L" -0.000002984 -2.304782867 0.000008970 0.771320243 1.401703054 4.314056763 0 0 0 0 0 0
$definebone "bip_ring_2_L" "bip_ring_1_L" 0.000003248 -2.038695097 -0.000005677 -4.344819935 14.211360309 32.906840553 0 0 0 0 0 0
$definebone "bip_pinky_0_L" "bip_hand_L" 1.909797311 -4.692568302 -1.954147100 102.795535462 26.198264609 38.413028288 0 0 0 0 0 0
$definebone "bip_pinky_1_L" "bip_pinky_0_L" 0.000002831 -1.611061811 0.000000119 2.751312469 3.034535868 2.111921812 0 0 0 0 0 0
$definebone "bip_pinky_2_L" "bip_pinky_1_L" 0.000000477 -1.348502755 0.000010252 -8.113246182 27.927584837 32.959883802 0 0 0 0 0 0
$definebone "collar_R" "bip_spine_3" -2.000000000 0.000005513 0.000000238 30.876624879 -29.893357676 41.755497472 0 0 0 0 0 0
$definebone "collar_L" "bip_spine_3" 2.000000000 0.000005513 0.000000238 -30.876624879 29.893357676 -138.244490462 0 0 0 0 0 0
$definebone "bip_neck" "bip_spine_3" 0.000000000 -5.374016285 -0.177789569 -0.000000000 0.000000000 11.285142490 0 0 0 0 0 0
$definebone "bip_head" "bip_neck" 0.000000000 -3.541619062 -0.535014689 -0.000000000 0.000000000 -6.261020969 0 0 0 0 0 0
$definebone "ponytail" "bip_head" 0.000000000 -1.937024474 3.120672703 -0.000000000 0.000000000 139.590133351 0 0 0 0 0 0
$definebone "bip_hip_L" "bip_pelvis" 2.628673077 0.049848754 -2.613191843 8.117584206 81.557308124 175.258965800 0 0 0 0 0 0
$definebone "bip_knee_L" "bip_hip_L" 12.181146622 0.000000447 0.000001013 18.541781351 -5.759627027 0.439686811 0 0 0 0 0 0
$definebone "bip_foot_L" "bip_knee_L" 16.169355392 0.000000432 -0.000002116 -1.639920416 86.781405632 -63.055623399 0 0 0 0 0 0
$definebone "bip_toe_L" "bip_foot_L" 0.000000399 -3.993541241 0.000000432 -0.567476822 1.539165841 -26.831829541 0 0 0 0 0 0
$definebone "spring_base_L" "bip_knee_L" 4.961766720 0.036237754 -2.589795113 -0.093060700 87.896427184 -177.772038283 0 0 0 0 0 0
$definebone "spring_end_L" "spring_base_L" 1.224202156 23.379367828 -1.143058300 -1.427757451 0.350418453 166.208787565 0 0 0 0 0 0
$definebone "spring_L" "spring_base_L" 0.935024202 20.687267303 3.230806351 -2.588782355 0.212533142 163.093565606 0 0 0 0 0 0
$definebone "bip_hip_R" "bip_pelvis" -2.628673077 0.049848754 -2.613191843 171.882420803 -81.557308124 4.741030671 0 0 0 0 0 0
$definebone "bip_knee_R" "bip_hip_R" 12.181147575 0.000000060 0.000000536 18.541779644 5.759627881 -0.439685477 0 0 0 0 0 0
$definebone "bip_foot_R" "bip_knee_R" 16.169357300 0.000000324 -0.000002235 1.639908036 93.218592547 116.944408931 0 0 0 0 0 0
$definebone "bip_toe_R" "bip_foot_R" 0.000001065 3.993541241 -0.000002608 -0.567481038 1.539148765 -26.831868815 0 0 0 0 0 0
$definebone "spring_base_R" "bip_knee_R" 4.961768150 -0.036237661 -2.589794874 0.093065396 92.103564165 2.227951358 0 0 0 0 0 0
$definebone "spring_end_R" "spring_base_R" -1.224198580 -23.379367828 1.143054962 -1.427758518 0.350418933 166.208787565 0 0 0 0 0 0
$definebone "spring_R" "spring_base_R" -0.935020924 -20.687267303 -3.230809212 -2.588784062 0.212533596 163.093565606 0 0 0 0 0 0
$definebone "weapon_bone" "bip_hand_R" 2.457207441 24.680942535 -2.581466198 98.656345202 54.410311457 -74.558775282 0 0 0 0 0 0
$definebone "forward" "bip_head" 0.000000000 -2.499156713 0.065124370 89.999988844 0.000000000 90.000009335 0 0 0 0 0 0
$definebone "thigh_twist_L" "bip_hip_L" 5.695569515 0.000000298 0.000000060 -0.000037673 0.000032550 -100.952320122 0 0 0 0 0 0
$definebone "thigh_twist_R" "bip_hip_R" 5.695569992 -0.000000328 -0.000000656 -0.000047118 -0.000005870 10.952266391 0 0 0 0 0 0
$definebone "Tail_1" "bip_pelvis" 0.107572533 -3.511920691 1.006515861 -0.000000127 0.000000034 -14.954593320 0 0 0 0 0 0
$definebone "Tail_2" "Tail_1" -0.000000001 0.000000477 5.249754429 0.000000117 -0.000000002 9.286358493 0 0 0 0 0 0
$definebone "Tail_3" "Tail_2" -0.000000012 0.000002027 8.363883018 0.000000001 -0.000000001 4.255046490 0 0 0 0 0 0
$definebone "Tail_4" "Tail_3" -0.000000011 0.000004932 0.685908437 0.000000010 -0.000000003 50.481521759 0 0 0 0 0 0
$definebone "LeftEye" "bip_head" 2.015471697 -6.399690151 -0.544794202 0.000000225 179.999991349 -88.507285152 0 0 0 0 0 0
$definebone "RightEye" "bip_head" -2.015471697 -6.399690151 -0.544794202 -0.000000225 -179.999991349 -88.507285152 0 0 0 0 0 0
$definebone "Ear.R" "bip_head" -4.140473843 -6.212677479 2.446212530 -0.147638061 157.372189345 -84.344196060 0 0 0 0 0 0
$definebone "Ear.R.002" "Ear.R" 0.000006445 0.000003070 1.942694545 -0.000405909 -0.000015368 -0.000000267 0 0 0 0 0 0
$definebone "Ear.R.001" "Ear.R.002" 0.000029236 -0.000000060 1.942679167 -0.000001281 -0.000001921 0.000003095 0 0 0 0 0 0
$definebone "Ear.R.003" "Ear.R.001" 0.000030112 0.000000179 1.942669988 0.000070026 -0.000010512 0.000003202 0 0 0 0 0 0
$definebone "Ear.L" "bip_head" 4.140473843 -6.212677479 2.446212530 0.147638061 -157.372189345 -84.344196060 0 0 0 0 0 0
$definebone "Ear.L.002" "Ear.L" -0.000006445 0.000003070 1.942694545 0.000405909 0.000015368 -0.000000267 0 0 0 0 0 0
$definebone "Ear.L.001" "Ear.L.002" -0.000029236 -0.000000060 1.942679167 0.000001281 0.000001921 0.000003095 0 0 0 0 0 0
$definebone "Ear.L.003" "Ear.L.001" -0.000030112 0.000000179 1.942669988 -0.000070026 0.000010512 0.000003202 0 0 0 0 0 0
$definebone "bicep_twist_L" "bip_upperArm_L" 4.691502094 -0.000000358 0.000001580 -79.822446905 -90.000924580 0.000841638 0 0 0 0 0 0
$definebone "Palm_01_L" "bip_hand_L" -0.476022512 -0.428182364 0.471465707 -51.548547572 143.468956799 46.352252349 0 0 0 0 0 0
$definebone "Palm_02_L" "bip_hand_L" 0.202547073 -0.890875936 -0.305104226 -55.545874802 157.179058916 36.077322158 0 0 0 0 0 0
$definebone "Palm_03_L" "bip_hand_L" 0.594023228 -1.215339541 -1.026863575 -54.159868910 165.910526865 31.849189175 0 0 0 0 0 0
$definebone "Palm_04_L" "bip_hand_L" 1.274671793 -1.988788486 -2.575719595 -57.668721502 172.512205226 24.101888307 0 0 0 0 0 0
$definebone "Palm_01_L.001" "bip_hand_L" -2.566137791 -5.675147057 1.349706650 -51.548574893 143.469052422 46.352057689 0 0 0 0 0 0
$definebone "MagBone.L" "bip_hand_L" -1.186924696 -1.021386147 2.349654913 -9.810392804 -83.742729602 15.625336679 0 0 0 0 0 0
$definebone "Magazine Follow.L" "MagBone.L" 1.904484987 8.546315193 -0.587080598 -2.300673876 -0.013061044 -89.991013976 0 0 0 0 0 0
$definebone "bicep_twist_R" "bip_upperArm_R" 4.691503525 0.000000961 -0.000000477 -169.822340127 90.000186920 -0.000026578 0 0 0 0 0 0
$definebone "Palm_01_R" "bip_hand_R" 0.476003408 -0.428189456 0.471470416 51.548458779 -143.469831063 46.352682651 0 0 0 0 0 0
$definebone "Palm_02_R" "bip_hand_R" -0.202571452 -0.890875161 -0.305096924 55.546086538 -157.179482388 36.078148611 0 0 0 0 0 0
$definebone "Palm_03_R" "bip_hand_R" -0.594053030 -1.215334177 -1.026854992 54.160008929 -165.911196223 31.849940496 0 0 0 0 0 0
$definebone "Palm_04_R" "bip_hand_R" -1.274719238 -1.988780856 -2.575709581 57.669090332 -172.512656018 24.102725005 0 0 0 0 0 0
$definebone "Breast_L" "bip_spine_3" 3.413403034 0.096739948 1.197661638 180.000005009 0.000008635 86.468596628 0 0 0 0 0 0
$definebone "Breast_R" "bip_spine_3" -3.413403034 0.096739948 1.197661638 180.000005009 0.000008635 86.468596628 0 0 0 0 0 0
$attachment "weapon_att" "weapon_bone" 0 0 0 rotate 0 0 0
$attachment "eyes" "bip_head" 0.00000000 -7.06794453 -1.61253726 rotate 88.50729198 -90.00000250 0.00000000
$attachment "forward" "forward" 0 0 0 rotate 0 0 0
$attachment "righteye" "bip_head" -2.58506989 -7.06794453 -1.61253726 rotate 88.50729198 -90.00000250 0.00000000
$attachment "lefteye" "bip_head" 2.58506989 -7.06794453 -1.61253726 rotate 88.50729198 -90.00000250 0.00000000
$poseparameter "body_pitch" -45 45 loop 360
$poseparameter "body_yaw" -45 45 loop 360

$sequence "ref" "proportion_basis.smd" fps 30
$sequence "ragdoll" "proportion_basis.smd" activity ACT_DIERAGDOLL 1 fps 30
$includemodel "player_animations.mdl"
$sequence "bowman_proportion_basis" "proportion_basis.smd" fps 1 hidden
$animation "a_bowman_proportions" "proportion_target.smd" subtract "bowman_proportion_basis" 0
$sequence "bowman_proportions" "a_bowman_proportions" delta autoplay hidden

$texturegroup "skinfamilies"
{
 { "eye_l" "eye_r" "eyeliner_head" "fluff" "fluff_head" "fur_blue" "fur_blue_head" "mouth_head" "paws" "teeth_head" }
 { "eye_l_orange" "eye_r_orange" "eyeliner_head" "fluff" "fluff_head" "fur_orange" "fur_orange_head" "mouth_head" "paws" "teeth_head" }
 { "silhouette" "silhouette" "silhouette" "silhouette" "silhouette" "silhouette" "silhouette" "silhouette" "silhouette" "silhouette" }
 { "nodraw" "nodraw" "nodraw" "fluff" "nodraw" "fur_blue" "nodraw" "nodraw" "paws" "nodraw" }
 { "nodraw" "nodraw" "nodraw" "fluff" "nodraw" "fur_orange" "nodraw" "nodraw" "paws" "nodraw" }
}



$ikchain "rhand" "bip_hand_R" knee 0 0 0
$ikchain "lhand" "bip_hand_L" knee 0 0 0
$ikchain "rfoot" "bip_foot_R" knee 0 0 0
$ikchain "lfoot" "bip_foot_L" knee 0 0 0

$collisionjoints "bowman_physics.smd"
{
	$mass 94
	$inertia 10
	$damping 0
	$rotdamping 0
	$rootbone "bip_pelvis"


	$jointmassbias "bip_hip_R" 0.8
	$jointrotdamping "bip_hip_R" 4
	$jointconstrain "bip_hip_R" x limit -50 39 0
	$jointconstrain "bip_hip_R" y limit -12 20 0
	$jointconstrain "bip_hip_R" z limit -23 8 0

	$jointmassbias "bip_knee_R" 1.2
	$jointrotdamping "bip_knee_R" 3
	$jointconstrain "bip_knee_R" x limit -12 41 0
	$jointconstrain "bip_knee_R" y limit -26 17 0
	$jointconstrain "bip_knee_R" z limit -15 -1 0

	$jointmassbias "bip_foot_R" 0.8
	$jointrotdamping "bip_foot_R" 7
	$jointconstrain "bip_foot_R" x limit -15 22 0
	$jointconstrain "bip_foot_R" y limit -28 12 0
	$jointconstrain "bip_foot_R" z limit -17 24 0

	$jointconstrain "bip_toe_R" x limit 0 28 0
	$jointconstrain "bip_toe_R" y limit -12 15 0
	$jointconstrain "bip_toe_R" z limit -12 10 0

	$jointconstrain "spring_base_R" x limit -3 6 0
	$jointconstrain "spring_base_R" y limit -37 23 0
	$jointconstrain "spring_base_R" z limit -8 3 0

	$jointconstrain "spring_end_R" x limit -23 17 0
	$jointconstrain "spring_end_R" y limit 0 19 0
	$jointconstrain "spring_end_R" z limit 0 0 0

	$jointmassbias "bip_hip_L" 0.8
	$jointrotdamping "bip_hip_L" 4
	$jointconstrain "bip_hip_L" x limit -64 50 0
	$jointconstrain "bip_hip_L" y limit -21 12 0
	$jointconstrain "bip_hip_L" z limit -23 8 0

	$jointmassbias "bip_knee_L" 1.2
	$jointrotdamping "bip_knee_L" 3
	$jointconstrain "bip_knee_L" x limit -12 66 0
	$jointconstrain "bip_knee_L" y limit -10 0 0
	$jointconstrain "bip_knee_L" z limit -6 6 0

	$jointconstrain "spring_base_L" x limit -6 3 0
	$jointconstrain "spring_base_L" y limit -15 15 0
	$jointconstrain "spring_base_L" z limit -6 6 0

	$jointmassbias "bip_foot_L" 0.8
	$jointrotdamping "bip_foot_L" 7
	$jointconstrain "bip_foot_L" x limit -32 21 0
	$jointconstrain "bip_foot_L" y limit -32 25 0
	$jointconstrain "bip_foot_L" z limit -17 24 0

	$jointconstrain "bip_toe_L" x limit 0 41 0
	$jointconstrain "bip_toe_L" y limit -19 6 0
	$jointconstrain "bip_toe_L" z limit -8 15 0

	$jointconstrain "spring_L" x limit 0 0 0
	$jointconstrain "spring_L" y limit 0 0 0
	$jointconstrain "spring_L" z limit 0 0 0

	$jointconstrain "spring_end_L" x limit -17 0 0
	$jointconstrain "spring_end_L" y limit -17 0 0
	$jointconstrain "spring_end_L" z limit 0 0 0

	$jointconstrain "bip_spine_2" x limit -37 17 0
	$jointconstrain "bip_spine_2" y limit -12 41 0
	$jointconstrain "bip_spine_2" z limit -20 15 0

	$jointmassbias "bip_upperArm_L" 0.8
	$jointrotdamping "bip_upperArm_L" 10
	$jointconstrain "bip_upperArm_L" x limit -64 68 0
	$jointconstrain "bip_upperArm_L" y limit -32 55 0
	$jointconstrain "bip_upperArm_L" z limit -35 57 0

	$jointmassbias "bip_lowerArm_L" 1.8
	$jointrotdamping "bip_lowerArm_L" 4
	$jointconstrain "bip_lowerArm_L" x limit 0 106 0
	$jointconstrain "bip_lowerArm_L" y limit -19 44 0
	$jointconstrain "bip_lowerArm_L" z limit -6 -1 0

	$jointmassbias "bip_hand_L" 0.6
	$jointrotdamping "bip_hand_L" 8
	$jointconstrain "bip_hand_L" x limit -30 37 0
	$jointconstrain "bip_hand_L" y limit -41 64 0
	$jointconstrain "bip_hand_L" z limit -53 26 0

	$jointmassbias "bip_upperArm_R" 0.8
	$jointrotdamping "bip_upperArm_R" 10
	$jointconstrain "bip_upperArm_R" x limit -50 68 0
	$jointconstrain "bip_upperArm_R" y limit -32 55 0
	$jointconstrain "bip_upperArm_R" z limit -35 55 0

	$jointmassbias "bip_lowerArm_R" 1.8
	$jointrotdamping "bip_lowerArm_R" 4
	$jointconstrain "bip_lowerArm_R" x limit 0 131 0
	$jointconstrain "bip_lowerArm_R" y limit -32 50 0
	$jointconstrain "bip_lowerArm_R" z limit -6 -6 0

	$jointmassbias "bip_hand_R" 0.6
	$jointrotdamping "bip_hand_R" 8
	$jointconstrain "bip_hand_R" x limit -37 30 0
	$jointconstrain "bip_hand_R" y limit -23 44 0
	$jointconstrain "bip_hand_R" z limit -28 20 0

	$jointmassbias "bip_head" 1.5
	$jointrotdamping "bip_head" 8
	$jointconstrain "bip_head" x limit -50 15 0
	$jointconstrain "bip_head" y limit -26 12 0
	$jointconstrain "bip_head" z limit -26 30 0

	$jointconstrain "spring_R" x limit 0 0 0
	$jointconstrain "spring_R" y limit 0 0 0
	$jointconstrain "spring_R" z limit 0 0 0
}

// Tail and ear secondary motion, shared with Portal 1 Bowman.
$jigglebone "Ear.R"
{
 is_flexible
 {
  length 1.942676
  tip_mass 2
  yaw_stiffness 250
  yaw_damping 8
  pitch_stiffness 250
  pitch_damping 8
  along_stiffness 600
  along_damping 8
  angle_constraint 9
  yaw_constraint -9 9
  pitch_constraint -9 9
 }
}

$jigglebone "Ear.R.002"
{
 is_flexible
 {
  length 1.942677
  tip_mass 2
  yaw_stiffness 250
  yaw_damping 8
  pitch_stiffness 250
  pitch_damping 8
  along_stiffness 600
  along_damping 8
  angle_constraint 9
  yaw_constraint -9 9
  pitch_constraint -9 9
 }
}

$jigglebone "Ear.R.001"
{
 is_flexible
 {
  length 1.942677
  tip_mass 2
  yaw_stiffness 250
  yaw_damping 8
  pitch_stiffness 250
  pitch_damping 8
  along_stiffness 600
  along_damping 8
  angle_constraint 9
  yaw_constraint -9 9
  pitch_constraint -9 9
 }
}

$jigglebone "Ear.R.003"
{
 is_flexible
 {
  length 1.942676
  tip_mass 2
  yaw_stiffness 250
  yaw_damping 8
  pitch_stiffness 250
  pitch_damping 8
  along_stiffness 600
  along_damping 8
  angle_constraint 9
  yaw_constraint -9 9
  pitch_constraint -9 9
 }
}

$jigglebone "Ear.L"
{
 is_flexible
 {
  length 1.942676
  tip_mass 2
  yaw_stiffness 250
  yaw_damping 8
  pitch_stiffness 250
  pitch_damping 8
  along_stiffness 600
  along_damping 8
  angle_constraint 9
  yaw_constraint -9 9
  pitch_constraint -9 9
 }
}

$jigglebone "Ear.L.002"
{
 is_flexible
 {
  length 1.942677
  tip_mass 2
  yaw_stiffness 250
  yaw_damping 8
  pitch_stiffness 250
  pitch_damping 8
  along_stiffness 600
  along_damping 8
  angle_constraint 9
  yaw_constraint -9 9
  pitch_constraint -9 9
 }
}

$jigglebone "Ear.L.001"
{
 is_flexible
 {
  length 1.942677
  tip_mass 2
  yaw_stiffness 250
  yaw_damping 8
  pitch_stiffness 250
  pitch_damping 8
  along_stiffness 600
  along_damping 8
  angle_constraint 9
  yaw_constraint -9 9
  pitch_constraint -9 9
 }
}

$jigglebone "Ear.L.003"
{
 is_flexible
 {
  length 1.942676
  tip_mass 2
  yaw_stiffness 250
  yaw_damping 8
  pitch_stiffness 250
  pitch_damping 8
  along_stiffness 600
  along_damping 8
  angle_constraint 9
  yaw_constraint -9 9
  pitch_constraint -9 9
 }
}

$jigglebone "Tail_1"
{
 is_flexible
 {
  length 5.249759
  tip_mass 6
  yaw_stiffness 110
  yaw_damping 8
  pitch_stiffness 110
  pitch_damping 8
  along_stiffness 600
  along_damping 8
  angle_constraint 17
  yaw_constraint -17 17
  pitch_constraint -17 17
 }
}

$jigglebone "Tail_2"
{
 is_flexible
 {
  length 8.363892
  tip_mass 6
  yaw_stiffness 110
  yaw_damping 8
  pitch_stiffness 110
  pitch_damping 8
  along_stiffness 600
  along_damping 8
  angle_constraint 17
  yaw_constraint -17 17
  pitch_constraint -17 17
 }
}

$jigglebone "Tail_3"
{
 is_flexible
 {
  length 0.750000
  tip_mass 6
  yaw_stiffness 110
  yaw_damping 8
  pitch_stiffness 110
  pitch_damping 8
  along_stiffness 600
  along_damping 8
  angle_constraint 17
  yaw_constraint -17 17
  pitch_constraint -17 17
 }
}

$jigglebone "Tail_4"
{
 is_flexible
 {
  length 8.289567
  tip_mass 6
  yaw_stiffness 110
  yaw_damping 8
  pitch_stiffness 110
  pitch_damping 8
  along_stiffness 600
  along_damping 8
  angle_constraint 17
  yaw_constraint -17 17
  pitch_constraint -17 17
 }
}

