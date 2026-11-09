"""Sliver 4c2e8d4 source in an unconfigured, inert Go 1.27.3 reference.

https://github.com/r0ny123/mcrit-data/issues/37

Only an analysis copy is adapted. The unexpanded generated export wrapper
is excluded; a separate main retains runner.Main's address without calling
it. First-party explicit initializers are renamed. The three existing OS
dispatch branches are selected, and Linux omits the Windows service adapter.
Keys, certificates, endpoints and configuration templates remain unexpanded.
No builder, profile generator, server or compiled program is run.

The runtime filter is based on Go package names, not version-specific hashes.
Go 1.27 runtime reference data is not claimed by this project contribution.
Vendored dependencies are retained and must not be counted as Sliver code.

Measured coverage (kept + removed = image total):
| target | kept | removed | total | project hashes >=10 |
| --- | --- | --- | --- | --- |
| 4c2e8d4/ELF/x64 | 12927 | 8811 | 21738 | 1374 |
| 4c2e8d4/ELF/x86 | 12120 | 10791 | 22911 | 1670 |
| 4c2e8d4/PE/x64 | 12118 | 8520 | 20638 | 1534 |
| 4c2e8d4/PE/x86 | 11741 | 8685 | 20426 | 1848 |

Qualifying named project PicHash intersections (functions >=10 instructions):
| target | 1.5.42/ELF/x64 | 1.5.42/ELF/x86 | 1.5.42/PE/x64 | 1.5.42/PE/x86 | 4c2e8d4/ELF/x64 | 4c2e8d4/ELF/x86 | 4c2e8d4/PE/x64 | 4c2e8d4/PE/x86 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.5.42/ELF/x64 | - | 0 | 987 | 0 | 0 | 0 | 0 | 0 |
| 1.5.42/ELF/x86 | 0 | - | 0 | 0 | 0 | 58 | 0 | 0 |
| 1.5.42/PE/x64 | 987 | 0 | - | 0 | 0 | 0 | 0 | 0 |
| 1.5.42/PE/x86 | 0 | 0 | 0 | - | 0 | 0 | 0 | 0 |
| 4c2e8d4/ELF/x64 | 0 | 0 | 0 | 0 | - | 0 | 1269 | 0 |
| 4c2e8d4/ELF/x86 | 0 | 58 | 0 | 0 | 0 | - | 0 | 0 |
| 4c2e8d4/PE/x64 | 0 | 0 | 0 | 0 | 1269 | 0 | - | 0 |
| 4c2e8d4/PE/x86 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - |

Project-hash counts exclude main/entry wrappers, init routines, unnamed
bodies and external namespaces. Source revision and compiler both change
between the two releases; these are measurements of their combined code
generation, not a claim that one change alone explains a difference.
New hashes outside the union of all four older reference images:
4c2e8d4/ELF/x64: 1374.
4c2e8d4/ELF/x86: 1612.
4c2e8d4/PE/x64: 1534.
4c2e8d4/PE/x86: 1848.

Retained namespace counts (kept totals are not first-party function counts):
4c2e8d4/ELF/x64: dependency=9705, first_party=1906, generated=408, startup=400, unnamed=508.
4c2e8d4/ELF/x86: dependency=8975, first_party=1906, generated=363, startup=396, unnamed=480.
4c2e8d4/PE/x64: dependency=9256, first_party=2119, generated=390, startup=353.
4c2e8d4/PE/x86: dependency=8498, first_party=2117, generated=336, startup=333, unnamed=457.

Named shared-hash examples; the paired MCRIT reports retain all names:
1.5.42/ELF/x86 / 4c2e8d4/ELF/x86: 8732507967509958337 [github.com/bishopfox/sliver/implant/sliver/netstack.checkResponse]; 42 instructions.
1.5.42/ELF/x86 / 4c2e8d4/ELF/x86: 6336159037963722901 [github.com/bishopfox/sliver/implant/sliver/proxy.ParseURL]; 34 instructions.
1.5.42/ELF/x86 / 4c2e8d4/ELF/x86: 10653499145695748641 [github.com/bishopfox/sliver/implant/sliver/netstack.(*Net).Dial]; 33 instructions.
4c2e8d4/ELF/x64 / 4c2e8d4/PE/x64: 4451897314405244668 [github.com/bishopfox/sliver/implant/sliver/handlers.searchFileForPattern]; 919 instructions.
4c2e8d4/ELF/x64 / 4c2e8d4/PE/x64: 7053697898663069516 [github.com/bishopfox/sliver/implant/sliver/netstack.(*Net).LookupContextHost]; 881 instructions.
4c2e8d4/ELF/x64 / 4c2e8d4/PE/x64: 14885243713061543902 [github.com/bishopfox/sliver/implant/sliver/handlers.executeHandler]; 849 instructions.

Changed entry/startup bodies, excluded from novelty:
4c2e8d4/ELF/x64: github.com/bishopfox/sliver/implant/sliver/runner.Main [40 instructions, 12081443071995271434]; main.main [21 instructions, 9280179623265941065].
4c2e8d4/ELF/x86: github.com/bishopfox/sliver/implant/sliver/runner.Main [47 instructions, 4581783535649718843]; main.main [21 instructions, 2510530606601308027].
4c2e8d4/PE/x64: github.com/bishopfox/sliver/implant/sliver/runner.Main [45 instructions, 8806743728693898369]; main.main [21 instructions, 9280179623265941065].
4c2e8d4/PE/x86: github.com/bishopfox/sliver/implant/sliver/runner.Main [56 instructions, 17800521521125970380]; main.main [22 instructions, 5391205391935206093].

Retained compiler-generated helpers outside the project namespace:
Primitive/anonymous array helpers can survive the existing Go filter.
They are excluded from project novelty; no source ownership is inferred.
type:.eq.EE: 4c2e8d4/ELF/x64 [36 instructions / 1813592308175480142 x1]; 4c2e8d4/ELF/x86 [38 instructions / 12565539715968394304 x1]; 4c2e8d4/PE/x64 [36 instructions / 1813592308175480142 x1]; 4c2e8d4/PE/x86 [39 instructions / 13526262980293106180 x1].
type:.eq.EEE: 4c2e8d4/ELF/x64 [47 instructions / 11202631260544237342 x1]; 4c2e8d4/ELF/x86 [52 instructions / 14523869431715488197 x1]; 4c2e8d4/PE/x64 [47 instructions / 11202631260544237342 x1]; 4c2e8d4/PE/x86 [53 instructions / 10952586667972145306 x1].
type:.eq.EEEE: 4c2e8d4/ELF/x86 [66 instructions / 5519180676208453161 x1]; 4c2e8d4/PE/x86 [67 instructions / 2857864479734891236 x1].
type:.eq.EES: 4c2e8d4/ELF/x64 [47 instructions / 3227977171857591235 x1]; 4c2e8d4/ELF/x86 [52 instructions / 18024996795833032635 x1]; 4c2e8d4/PE/x64 [47 instructions / 3227977171857591235 x1]; 4c2e8d4/PE/x86 [53 instructions / 13555674882122447221 x1].
type:.eq.EI: 4c2e8d4/ELF/x64 [36 instructions / 1813592308175480142 x1]; 4c2e8d4/ELF/x86 [38 instructions / 12565539715968394304 x1]; 4c2e8d4/PE/x64 [36 instructions / 1813592308175480142 x1]; 4c2e8d4/PE/x86 [39 instructions / 13526262980293106180 x1].
type:.eq.EIM1: 4c2e8d4/ELF/x64 [43 instructions / 67569233449919211 x1]; 4c2e8d4/ELF/x86 [45 instructions / 6339229213038005663 x1]; 4c2e8d4/PE/x64 [43 instructions / 67569233449919211 x1]; 4c2e8d4/PE/x86 [46 instructions / 7359515000242125983 x1].
type:.eq.EM112: 4c2e8d4/ELF/x64 [34 instructions / 7782197849794772837 x1]; 4c2e8d4/PE/x64 [34 instructions / 7782197849794772837 x1].
type:.eq.EM120: 4c2e8d4/ELF/x86 [35 instructions / 7059296959050137190 x1]; 4c2e8d4/PE/x86 [36 instructions / 18159391051004889455 x1].
type:.eq.EM16: 4c2e8d4/ELF/x64 [37 instructions / 7979892414358577792 x1]; 4c2e8d4/PE/x64 [37 instructions / 7979892414358577792 x1].
type:.eq.EM40: 4c2e8d4/ELF/x86 [71 instructions / 16940347856311191009 x1]; 4c2e8d4/PE/x86 [72 instructions / 14228486524658496203 x1].
type:.eq.EM76: 4c2e8d4/ELF/x64 [34 instructions / 8878888018611761407 x1]; 4c2e8d4/PE/x64 [34 instructions / 8878888018611761407 x1].
type:.eq.EM8: 4c2e8d4/ELF/x86 [35 instructions / 5812457356089579775 x1]; 4c2e8d4/PE/x86 [36 instructions / 15717611146232747738 x1].
type:.eq.GGGGGGM2: 4c2e8d4/ELF/x64 [37 instructions / 11500763807416260768 x1]; 4c2e8d4/ELF/x86 [45 instructions / 2680061384212280876 x1]; 4c2e8d4/PE/x64 [37 instructions / 11500763807416260768 x1]; 4c2e8d4/PE/x86 [46 instructions / 14569260740428323535 x1].
type:.eq.GGM16GGGGGM40: 4c2e8d4/ELF/x86 [108 instructions / 15908905466884182632 x1]; 4c2e8d4/PE/x86 [109 instructions / 11886988059361560836 x1].
type:.eq.GGM16GGGGGM48: 4c2e8d4/ELF/x86 [117 instructions / 4805197014744331752 x1]; 4c2e8d4/PE/x86 [118 instructions / 7554307096245131268 x1].
type:.eq.GGM16GGGGGM4K4M40: 4c2e8d4/ELF/x64 [66 instructions / 4708874602372424938 x1]; 4c2e8d4/PE/x64 [66 instructions / 4708874602372424938 x1].
type:.eq.GGM16GGGGGM4K4M56: 4c2e8d4/ELF/x64 [73 instructions / 17041683138080424831 x1]; 4c2e8d4/PE/x64 [73 instructions / 17041683138080424831 x1].
type:.eq.IEE: 4c2e8d4/ELF/x64 [47 instructions / 11202631260544237342 x1]; 4c2e8d4/ELF/x86 [52 instructions / 14523869431715488197 x1]; 4c2e8d4/PE/x64 [47 instructions / 11202631260544237342 x1]; 4c2e8d4/PE/x86 [53 instructions / 10952586667972145306 x1].
type:.eq.IEM4: 4c2e8d4/ELF/x86 [45 instructions / 6471782647867066940 x1]; 4c2e8d4/PE/x86 [46 instructions / 13929036363295089163 x1].
type:.eq.IEM8: 4c2e8d4/ELF/x64 [43 instructions / 16019897944208919326 x1]; 4c2e8d4/PE/x64 [43 instructions / 16019897944208919326 x1].
type:.eq.II: 4c2e8d4/ELF/x64 [36 instructions / 1813592308175480142 x1]; 4c2e8d4/ELF/x86 [38 instructions / 12565539715968394304 x1]; 4c2e8d4/PE/x64 [36 instructions / 1813592308175480142 x1]; 4c2e8d4/PE/x86 [39 instructions / 13526262980293106180 x1].
type:.eq.III: 4c2e8d4/ELF/x64 [47 instructions / 11202631260544237342 x1]; 4c2e8d4/ELF/x86 [52 instructions / 14523869431715488197 x1]; 4c2e8d4/PE/x64 [47 instructions / 11202631260544237342 x1]; 4c2e8d4/PE/x86 [53 instructions / 10952586667972145306 x1].
type:.eq.IIIIM4: 4c2e8d4/ELF/x64 [65 instructions / 6059042708005147490 x1]; 4c2e8d4/ELF/x86 [73 instructions / 1769004206649940340 x1]; 4c2e8d4/PE/x64 [65 instructions / 6059042708005147490 x1]; 4c2e8d4/PE/x86 [74 instructions / 3571690622789550726 x1].
type:.eq.IIIM24: 4c2e8d4/ELF/x64 [62 instructions / 1132087074817755076 x1]; 4c2e8d4/ELF/x86 [81 instructions / 5835681643667804481 x1]; 4c2e8d4/PE/x64 [62 instructions / 1132087074817755076 x1]; 4c2e8d4/PE/x86 [82 instructions / 7927124998985947777 x1].
type:.eq.IIM16SSSM4K4M39: 4c2e8d4/ELF/x64 [101 instructions / 4588226462305746024 x1]; 4c2e8d4/PE/x64 [101 instructions / 4588226462305746024 x1].
type:.eq.IIM2: 4c2e8d4/ELF/x64 [43 instructions / 1067803153430313330 x1]; 4c2e8d4/ELF/x86 [45 instructions / 3098643547154145875 x1]; 4c2e8d4/PE/x64 [43 instructions / 1067803153430313330 x1]; 4c2e8d4/PE/x86 [46 instructions / 15993687141925657156 x1].
type:.eq.IIM2K2IM4: 4c2e8d4/ELF/x86 [62 instructions / 11560263958257741720 x1]; 4c2e8d4/PE/x86 [63 instructions / 688633117771788475 x1].
type:.eq.IIM2K6IM4: 4c2e8d4/ELF/x64 [58 instructions / 9017472034892729490 x1]; 4c2e8d4/PE/x64 [58 instructions / 9017472034892729490 x1].
type:.eq.IIM8SSSM27: 4c2e8d4/ELF/x86 [133 instructions / 2799786995886475008 x1]; 4c2e8d4/PE/x86 [134 instructions / 18386027544725869513 x1].
type:.eq.IIM9: 4c2e8d4/ELF/x64 [47 instructions / 10712141885348938453 x1]; 4c2e8d4/ELF/x86 [54 instructions / 9982000595449113266 x1]; 4c2e8d4/PE/x64 [47 instructions / 10712141885348938453 x1]; 4c2e8d4/PE/x86 [55 instructions / 6468323283327012192 x1].
type:.eq.IIS: 4c2e8d4/ELF/x64 [47 instructions / 3227977171857591235 x1]; 4c2e8d4/ELF/x86 [52 instructions / 18024996795833032635 x1]; 4c2e8d4/PE/x64 [47 instructions / 3227977171857591235 x1]; 4c2e8d4/PE/x86 [53 instructions / 13555674882122447221 x1].
type:.eq.IM1: 4c2e8d4/ELF/x64 [34 instructions / 6021436321469853005 x1]; 4c2e8d4/ELF/x86 [31 instructions / 10102173048269801792 x1]; 4c2e8d4/PE/x64 [34 instructions / 6021436321469853005 x1]; 4c2e8d4/PE/x86 [32 instructions / 3940413926621824132 x1].
type:.eq.IM10: 4c2e8d4/ELF/x64 [37 instructions / 4896161333722607600 x1]; 4c2e8d4/ELF/x86 [40 instructions / 10437868661579083697 x1]; 4c2e8d4/PE/x64 [37 instructions / 4896161333722607600 x1]; 4c2e8d4/PE/x86 [41 instructions / 545660022903598332 x1].
type:.eq.IM11K1M16IM1269: 4c2e8d4/ELF/x86 [79 instructions / 2259970948438950090 x1]; 4c2e8d4/PE/x86 [80 instructions / 3471408849165562959 x1].
type:.eq.IM11K5M32IM1277: 4c2e8d4/ELF/x64 [66 instructions / 17958930108589694654 x1]; 4c2e8d4/PE/x64 [66 instructions / 17958930108589694654 x1].
type:.eq.IM12: 4c2e8d4/ELF/x64 [36 instructions / 14850667596304833491 x1]; 4c2e8d4/ELF/x86 [40 instructions / 7950333972909625352 x1]; 4c2e8d4/PE/x64 [36 instructions / 14850667596304833491 x1]; 4c2e8d4/PE/x86 [41 instructions / 7424432320386694359 x1].
type:.eq.IM16: 4c2e8d4/ELF/x64 [37 instructions / 7979892414358577792 x1]; 4c2e8d4/ELF/x86 [44 instructions / 9912570288451907220 x1]; 4c2e8d4/PE/x64 [37 instructions / 7979892414358577792 x1].
type:.eq.IM16I: 4c2e8d4/ELF/x64 [42 instructions / 10358325207025255173 x1]; 4c2e8d4/ELF/x86 [56 instructions / 10560796385316545061 x1]; 4c2e8d4/PE/x64 [42 instructions / 10358325207025255173 x1]; 4c2e8d4/PE/x86 [57 instructions / 2543723647198630358 x1].
type:.eq.IM1K3M4: 4c2e8d4/ELF/x64 [36 instructions / 17839814698280892930 x1]; 4c2e8d4/ELF/x86 [34 instructions / 1603404145388380097 x1]; 4c2e8d4/PE/x64 [36 instructions / 17839814698280892930 x1]; 4c2e8d4/PE/x86 [35 instructions / 2728751297907210643 x1].
type:.eq.IM1K7M8: 4c2e8d4/ELF/x64 [36 instructions / 12451008022684200100 x1]; 4c2e8d4/PE/x64 [36 instructions / 12451008022684200100 x1].
type:.eq.IM2: 4c2e8d4/ELF/x64 [33 instructions / 4124298352083001347 x1]; 4c2e8d4/ELF/x86 [31 instructions / 10901072777444320786 x1]; 4c2e8d4/PE/x64 [33 instructions / 4124298352083001347 x1]; 4c2e8d4/PE/x86 [32 instructions / 11980725067750780324 x1].
type:.eq.IM20: 4c2e8d4/ELF/x86 [49 instructions / 16452414281742771290 x1]; 4c2e8d4/PE/x86 [50 instructions / 8734113692905087541 x1].
type:.eq.IM20K4I: 4c2e8d4/ELF/x64 [45 instructions / 11251272704586641256 x1]; 4c2e8d4/PE/x64 [45 instructions / 11251272704586641256 x1].
type:.eq.IM20K4M40: 4c2e8d4/ELF/x64 [56 instructions / 15238596806092917432 x1]; 4c2e8d4/PE/x64 [56 instructions / 15238596806092917432 x1].
type:.eq.IM24: 4c2e8d4/ELF/x64 [39 instructions / 18046482323718885754 x1]; 4c2e8d4/ELF/x86 [53 instructions / 6187081001114000489 x1]; 4c2e8d4/PE/x64 [39 instructions / 18046482323718885754 x1]; 4c2e8d4/PE/x86 [54 instructions / 13435079695973661732 x1].
type:.eq.IM26: 4c2e8d4/ELF/x86 [58 instructions / 3536080885054372861 x1]; 4c2e8d4/PE/x86 [59 instructions / 6732817663201223667 x1].
type:.eq.IM2K2IM8: 4c2e8d4/ELF/x86 [52 instructions / 8885724738102382703 x1]; 4c2e8d4/PE/x86 [53 instructions / 13097747209190541526 x1].
type:.eq.IM2K2M8: 4c2e8d4/ELF/x86 [38 instructions / 2628337288468326959 x1]; 4c2e8d4/PE/x86 [39 instructions / 8417814476904302671 x1].
type:.eq.IM2K6IM4K4M8: 4c2e8d4/ELF/x64 [50 instructions / 3045443357793621850 x1]; 4c2e8d4/PE/x64 [50 instructions / 3045443357793621850 x1].
type:.eq.IM2K6M8: 4c2e8d4/ELF/x64 [37 instructions / 4992342660705793843 x1]; 4c2e8d4/PE/x64 [37 instructions / 4992342660705793843 x1].
type:.eq.IM32: 4c2e8d4/ELF/x64 [43 instructions / 4969906429873468125 x1]; 4c2e8d4/ELF/x86 [62 instructions / 3200285437786364040 x1]; 4c2e8d4/PE/x64 [43 instructions / 4969906429873468125 x1]; 4c2e8d4/PE/x86 [63 instructions / 9720633479660614159 x1].
type:.eq.IM34: 4c2e8d4/ELF/x64 [45 instructions / 16471850188699423387 x1]; 4c2e8d4/PE/x64 [45 instructions / 16471850188699423387 x1].
type:.eq.IM37K3FFM9K3M52FF: 4c2e8d4/ELF/x86 [163 instructions / 16871334604278218963 x1]; 4c2e8d4/PE/x86 [164 instructions / 16536528077710424931 x1].
type:.eq.IM4: 4c2e8d4/ELF/x64 [34 instructions / 10705299786855341506 x1]; 4c2e8d4/ELF/x86 [31 instructions / 8384016577967248861 x1]; 4c2e8d4/PE/x64 [34 instructions / 10705299786855341506 x1]; 4c2e8d4/PE/x86 [32 instructions / 9771535256791098189 x1].
type:.eq.IM40: 4c2e8d4/ELF/x64 [45 instructions / 14934607531993048074 x1]; 4c2e8d4/PE/x64 [45 instructions / 14934607531993048074 x1].
type:.eq.IM41K3FFK4M9K7M28K4M24FF: 4c2e8d4/ELF/x64 [104 instructions / 946852411516934224 x1]; 4c2e8d4/PE/x64 [104 instructions / 946852411516934224 x1].
type:.eq.IM4IM3K1M1028: 4c2e8d4/ELF/x86 [58 instructions / 3918583545377961603 x1]; 4c2e8d4/PE/x86 [59 instructions / 2397913482907648908 x1].
type:.eq.IM4K4M16: 4c2e8d4/ELF/x64 [40 instructions / 4885456454744482096 x1].
type:.eq.IM60: 4c2e8d4/ELF/x86 [94 instructions / 5946993011961341514 x1]; 4c2e8d4/PE/x86 [95 instructions / 17490188888277231272 x1].
type:.eq.IM8: 4c2e8d4/ELF/x64 [33 instructions / 11287464466772992982 x1]; 4c2e8d4/ELF/x86 [35 instructions / 5812457356089579775 x1]; 4c2e8d4/PE/x64 [33 instructions / 11287464466772992982 x1]; 4c2e8d4/PE/x86 [36 instructions / 15717611146232747738 x1].
type:.eq.IM8IM3K5M1032: 4c2e8d4/ELF/x64 [55 instructions / 5737998758915353442 x1]; 4c2e8d4/PE/x64 [55 instructions / 5737998758915353442 x1].
type:.eq.IM8IM512I: 4c2e8d4/ELF/x64 [59 instructions / 15587226017439796152 x1]; 4c2e8d4/ELF/x86 [72 instructions / 6617959283274654089 x1]; 4c2e8d4/PE/x64 [59 instructions / 15587226017439796152 x1]; 4c2e8d4/PE/x86 [73 instructions / 259196035616903323 x1].
type:.eq.IS: 4c2e8d4/ELF/x64 [36 instructions / 11439400506701595561 x1]; 4c2e8d4/ELF/x86 [38 instructions / 12112893081963180335 x1]; 4c2e8d4/PE/x64 [36 instructions / 11439400506701595561 x1]; 4c2e8d4/PE/x86 [39 instructions / 6139932407429436965 x1].
type:.eq.ISIM2K2M4: 4c2e8d4/ELF/x86 [62 instructions / 13485951577437882381 x1]; 4c2e8d4/PE/x86 [63 instructions / 14010915627320485600 x1].
type:.eq.ISIM2K6M8: 4c2e8d4/ELF/x64 [58 instructions / 1368866497184082837 x1]; 4c2e8d4/PE/x64 [58 instructions / 1368866497184082837 x1].
type:.eq.ISM2: 4c2e8d4/PE/x64 [40 instructions / 16727125814254129125 x1]; 4c2e8d4/PE/x86 [42 instructions / 4147532776711535014 x1].
type:.eq.ISS: 4c2e8d4/PE/x64 [47 instructions / 18010701497424813383 x1]; 4c2e8d4/PE/x86 [54 instructions / 6681025358742625642 x1].
type:.eq.ISSSM16: 4c2e8d4/ELF/x64 [66 instructions / 369230177028876343 x1]; 4c2e8d4/ELF/x86 [94 instructions / 887067694865243009 x1]; 4c2e8d4/PE/x64 [66 instructions / 369230177028876343 x1]; 4c2e8d4/PE/x86 [95 instructions / 12631495040936338087 x1].
type:.eq.ISSSM3: 4c2e8d4/ELF/x64 [66 instructions / 7717483186543710711 x1]; 4c2e8d4/ELF/x86 [74 instructions / 16517803127774764706 x1]; 4c2e8d4/PE/x64 [66 instructions / 7717483186543710711 x1]; 4c2e8d4/PE/x86 [75 instructions / 13146041599760048184 x1].
type:.eq.M1078K2M2720: 4c2e8d4/ELF/x86 [30 instructions / 5570550517423896152 x1]; 4c2e8d4/PE/x86 [31 instructions / 15862912309008819394 x1].
type:.eq.M10K2M22K2M48: 4c2e8d4/ELF/x86 [103 instructions / 3101198285590221803 x1]; 4c2e8d4/PE/x86 [104 instructions / 16837379048436919022 x1].
type:.eq.M10K6M16IM12: 4c2e8d4/ELF/x64 [51 instructions / 1248779844371973422 x1]; 4c2e8d4/PE/x64 [51 instructions / 1248779844371973422 x1].
type:.eq.M10K6M24: 4c2e8d4/ELF/x64 [18 instructions / 5788144615881550431 x1].
type:.eq.M10K6M26K6M28K4M28: 4c2e8d4/ELF/x64 [49 instructions / 3944751915759921545 x1]; 4c2e8d4/PE/x64 [49 instructions / 3944751915759921545 x1].
type:.eq.M11K1M13: 4c2e8d4/ELF/x64 [15 instructions / 14140599288060330146 x1]; 4c2e8d4/ELF/x86 [40 instructions / 12323131984503008672 x1].
type:.eq.M11K5M5K3M28: 4c2e8d4/ELF/x64 [29 instructions / 15417849540746489245 x1]; 4c2e8d4/PE/x64 [29 instructions / 15417849540746489245 x1].
type:.eq.M11K5M8: 4c2e8d4/ELF/x64 [12 instructions / 4006433805479132680 x1]; 4c2e8d4/PE/x64 [12 instructions / 4006433805479132680 x1].
type:.eq.M12E: 4c2e8d4/ELF/x86 [36 instructions / 17712729797659075081 x1]; 4c2e8d4/PE/x86 [37 instructions / 367095416462546689 x1].
type:.eq.M12EM4: 4c2e8d4/ELF/x86 [43 instructions / 8505467982640840943 x1]; 4c2e8d4/PE/x86 [44 instructions / 18200488710984509664 x1].
type:.eq.M12I: 4c2e8d4/ELF/x86 [36 instructions / 17712729797659075081 x1]; 4c2e8d4/PE/x86 [37 instructions / 367095416462546689 x1].
type:.eq.M12II: 4c2e8d4/ELF/x86 [50 instructions / 12945049212137765767 x1]; 4c2e8d4/PE/x86 [51 instructions / 10912546141407029993 x1].
type:.eq.M12IIM4IM4IEM4SSS: 4c2e8d4/ELF/x86 [145 instructions / 10804406494208217747 x1]; 4c2e8d4/PE/x86 [146 instructions / 2043707986670440294 x1].
type:.eq.M12IM3K1M8: 4c2e8d4/ELF/x86 [53 instructions / 10112204904505201079 x1]; 4c2e8d4/PE/x86 [54 instructions / 14906643939099625232 x1].
type:.eq.M12K4I: 4c2e8d4/ELF/x64 [31 instructions / 12740460259176020760 x1]; 4c2e8d4/PE/x64 [31 instructions / 12740460259176020760 x1].
type:.eq.M12K4IIM8IM8IEM4K4SSS: 4c2e8d4/ELF/x64 [119 instructions / 15936073506522457253 x1]; 4c2e8d4/PE/x64 [119 instructions / 15936073506522457253 x1].
type:.eq.M12K4M12K4M4K4M12: 4c2e8d4/PE/x64 [25 instructions / 398817587330784436 x1].
type:.eq.M12K4M16: 4c2e8d4/ELF/x64 [15 instructions / 8087969643918641690 x1]; 4c2e8d4/ELF/x86 [40 instructions / 8917518162024635359 x1]; 4c2e8d4/PE/x64 [15 instructions / 8087969643918641690 x1]; 4c2e8d4/PE/x86 [41 instructions / 15917401982180087574 x1].
type:.eq.M12K4M24IM10K2M5: 4c2e8d4/ELF/x64 [59 instructions / 7814998569082308345 x1]; 4c2e8d4/PE/x64 [59 instructions / 7814998569082308345 x1].
type:.eq.M12K4M24IM6K2M5: 4c2e8d4/ELF/x86 [79 instructions / 17060603000414495048 x1]; 4c2e8d4/PE/x86 [80 instructions / 8323545797763643074 x1].
type:.eq.M12K4M26K6M16: 4c2e8d4/ELF/x64 [29 instructions / 11862544228455812501 x1]; 4c2e8d4/PE/x64 [29 instructions / 11862544228455812501 x1].
type:.eq.M12K4M48: 4c2e8d4/ELF/x64 [29 instructions / 2644123177404420105 x1]; 4c2e8d4/PE/x64 [29 instructions / 2644123177404420105 x1].
type:.eq.M12K4M48IM8: 4c2e8d4/ELF/x64 [57 instructions / 12401163592837353027 x1]; 4c2e8d4/PE/x64 [57 instructions / 12401163592837353027 x1].
type:.eq.M12K4M52K4M17K7M8: 4c2e8d4/ELF/x64 [45 instructions / 7032215247198751062 x1]; 4c2e8d4/PE/x64 [45 instructions / 7032215247198751062 x1].
type:.eq.M12K4M57K7M44K4M10: 4c2e8d4/ELF/x64 [62 instructions / 11069391709801788607 x1]; 4c2e8d4/PE/x64 [62 instructions / 11069391709801788607 x1].
type:.eq.M12K4M8: 4c2e8d4/ELF/x64 [12 instructions / 8145274846608023740 x1]; 4c2e8d4/ELF/x86 [31 instructions / 1646719271133174484 x1]; 4c2e8d4/PE/x64 [12 instructions / 8145274846608023740 x1].
type:.eq.M12K4M9: 4c2e8d4/ELF/x64 [15 instructions / 10895933566934879168 x1]; 4c2e8d4/PE/x64 [15 instructions / 10895933566934879168 x1].
type:.eq.M12S: 4c2e8d4/ELF/x86 [36 instructions / 16598964044991032074 x1]; 4c2e8d4/PE/x86 [37 instructions / 9557190136610561743 x1].
type:.eq.M13K3M22K2M22K2M8: 4c2e8d4/ELF/x86 [91 instructions / 16145286982243715571 x1]; 4c2e8d4/PE/x86 [92 instructions / 8472217493178473523 x1].
type:.eq.M13K3M24: 4c2e8d4/ELF/x86 [55 instructions / 4450205124222041719 x1].
type:.eq.M13K3M308: 4c2e8d4/ELF/x86 [39 instructions / 12912841912589867329 x1]; 4c2e8d4/PE/x86 [40 instructions / 8642461955315016342 x1].
type:.eq.M13K3M5: 4c2e8d4/PE/x86 [37 instructions / 3861340006035614169 x1].
type:.eq.M13K3M5K3M4: 4c2e8d4/ELF/x86 [39 instructions / 17707019577582020565 x1]; 4c2e8d4/PE/x86 [40 instructions / 1722968611246127013 x1].
type:.eq.M13K3M5K3M8: 4c2e8d4/ELF/x64 [19 instructions / 890698961531376974 x1]; 4c2e8d4/PE/x64 [19 instructions / 890698961531376974 x1].
type:.eq.M13K3M76: 4c2e8d4/ELF/x86 [39 instructions / 15948864985102049243 x1]; 4c2e8d4/PE/x86 [40 instructions / 16611970869874827011 x1].
type:.eq.M148K4M16IM1K3M4: 4c2e8d4/ELF/x64 [48 instructions / 9295276070757477067 x1]; 4c2e8d4/PE/x64 [48 instructions / 9295276070757477067 x1].
type:.eq.M14K2M12: 4c2e8d4/ELF/x64 [15 instructions / 16227612206541487949 x1]; 4c2e8d4/ELF/x86 [42 instructions / 11987568141917285559 x1].
type:.eq.M14K2M18K2M25K3M2K2M5K3M10K2M1K3M4: 4c2e8d4/ELF/x86 [108 instructions / 5594960235855285806 x1]; 4c2e8d4/PE/x86 [109 instructions / 14404239308034457433 x1].
type:.eq.M14K2M20: 4c2e8d4/ELF/x86 [51 instructions / 17661166786125511349 x1].
type:.eq.M14K2M44: 4c2e8d4/ELF/x86 [78 instructions / 10811944354367744837 x1]; 4c2e8d4/PE/x86 [79 instructions / 587308336937636025 x1].
type:.eq.M14K2SM2K2M77K3M4: 4c2e8d4/ELF/x86 [60 instructions / 2765697136980996967 x1].
type:.eq.M14K2SM2K2M77K7M8: 4c2e8d4/ELF/x64 [47 instructions / 15561179662391896401 x1].
type:.eq.M152IM1K3M4: 4c2e8d4/ELF/x86 [43 instructions / 3810561544280988285 x1]; 4c2e8d4/PE/x86 [44 instructions / 17821135390769395472 x1].
type:.eq.M16I: 4c2e8d4/ELF/x64 [32 instructions / 6050074267886213762 x1]; 4c2e8d4/ELF/x86 [42 instructions / 13679084504620991012 x1]; 4c2e8d4/PE/x64 [32 instructions / 6050074267886213762 x1]; 4c2e8d4/PE/x86 [43 instructions / 3959207678443274760 x1].
type:.eq.M16IIM12K4M26K6SM4K4M26K6SM4: 4c2e8d4/ELF/x64 [105 instructions / 9230988622632952354 x1]; 4c2e8d4/PE/x64 [105 instructions / 9230988622632952354 x1].
type:.eq.M16IM3K5M8: 4c2e8d4/ELF/x64 [48 instructions / 5284630956162034427 x1]; 4c2e8d4/PE/x64 [48 instructions / 5284630956162034427 x1].
type:.eq.M16IM40: 4c2e8d4/ELF/x64 [54 instructions / 4777243114968183337 x1]; 4c2e8d4/PE/x64 [54 instructions / 4777243114968183337 x1].
type:.eq.M16IM8: 4c2e8d4/ELF/x64 [40 instructions / 7949966428082810160 x1]; 4c2e8d4/PE/x64 [40 instructions / 7949966428082810160 x1].
type:.eq.M16K4M20: 4c2e8d4/ELF/x86 [51 instructions / 14195923513524407432 x1]; 4c2e8d4/PE/x86 [52 instructions / 9390829835458662040 x1].
type:.eq.M16S: 4c2e8d4/ELF/x64 [29 instructions / 5620733540601748381 x1]; 4c2e8d4/ELF/x86 [42 instructions / 13542413249281426475 x1]; 4c2e8d4/PE/x64 [29 instructions / 5620733540601748381 x1]; 4c2e8d4/PE/x86 [43 instructions / 4796485472261741787 x1].
type:.eq.M16SM16I: 4c2e8d4/ELF/x64 [49 instructions / 14989048748261616555 x1]; 4c2e8d4/PE/x64 [49 instructions / 14989048748261616555 x1].
type:.eq.M16SS: 4c2e8d4/ELF/x64 [42 instructions / 15174265506728072413 x1].
type:.eq.M16SSM12EES: 4c2e8d4/ELF/x86 [115 instructions / 14268521602474968871 x1]; 4c2e8d4/PE/x86 [116 instructions / 12559859175306535289 x1].
type:.eq.M16SSM16EES: 4c2e8d4/ELF/x64 [81 instructions / 768930749539267655 x1]; 4c2e8d4/PE/x64 [81 instructions / 768930749539267655 x1].
type:.eq.M16SSM40: 4c2e8d4/ELF/x64 [58 instructions / 18367763734003512409 x1]; 4c2e8d4/PE/x64 [58 instructions / 18367763734003512409 x1].
type:.eq.M17K3M12: 4c2e8d4/ELF/x86 [45 instructions / 13467101319337566779 x1]; 4c2e8d4/PE/x86 [46 instructions / 8944819660136467248 x1].
type:.eq.M17K3M24: 4c2e8d4/ELF/x64 [22 instructions / 2321053856620054990 x1].
type:.eq.M17K3M2K2M20: 4c2e8d4/ELF/x86 [57 instructions / 16950108437295615142 x1].
type:.eq.M17K3S: 4c2e8d4/ELF/x86 [45 instructions / 725058137494598767 x1].
type:.eq.M17K7M17K7I: 4c2e8d4/ELF/x64 [44 instructions / 9460099532830979656 x1]; 4c2e8d4/PE/x64 [44 instructions / 9460099532830979656 x1].
type:.eq.M17K7M20: 4c2e8d4/ELF/x64 [22 instructions / 3366788935662782040 x1]; 4c2e8d4/PE/x64 [22 instructions / 3366788935662782040 x1].
type:.eq.M17K7M20K4M8: 4c2e8d4/ELF/x64 [25 instructions / 17596273442848001417 x1]; 4c2e8d4/PE/x64 [25 instructions / 17596273442848001417 x1].
type:.eq.M17K7M84: 4c2e8d4/ELF/x64 [31 instructions / 16248852888518164930 x1]; 4c2e8d4/PE/x64 [31 instructions / 16248852888518164930 x1].
type:.eq.M17K7M9: 4c2e8d4/PE/x64 [19 instructions / 16038353428554758794 x1].
type:.eq.M17K7M9K7M27: 4c2e8d4/ELF/x64 [32 instructions / 17922745342092736583 x1]; 4c2e8d4/PE/x64 [32 instructions / 17922745342092736583 x1].
type:.eq.M17K7S: 4c2e8d4/ELF/x64 [32 instructions / 14192820922024925360 x1].
type:.eq.M18K2M20: 4c2e8d4/ELF/x64 [21 instructions / 6296419584353920736 x1].
type:.eq.M1K3I: 4c2e8d4/ELF/x86 [27 instructions / 295478182898907141 x1]; 4c2e8d4/PE/x86 [28 instructions / 15178254677305822864 x1].
type:.eq.M1K3IM4: 4c2e8d4/ELF/x86 [34 instructions / 2332720602579229186 x1]; 4c2e8d4/PE/x86 [35 instructions / 835024974311488684 x1].
type:.eq.M1K3M12: 4c2e8d4/ELF/x86 [27 instructions / 698020368482012415 x1]; 4c2e8d4/PE/x86 [28 instructions / 14650477185783023872 x1].
type:.eq.M1K3M12SS: 4c2e8d4/ELF/x64 [44 instructions / 3496092862710894041 x1]; 4c2e8d4/ELF/x86 [54 instructions / 14504767143679743607 x1]; 4c2e8d4/PE/x64 [44 instructions / 3496092862710894041 x1]; 4c2e8d4/PE/x86 [55 instructions / 12478171803419417094 x1].
type:.eq.M1K3M16: 4c2e8d4/ELF/x86 [31 instructions / 3493021231969743137 x1]; 4c2e8d4/PE/x86 [32 instructions / 16829562828333858620 x1].
type:.eq.M1K3M16[2M32]: 4c2e8d4/ELF/x86 [54 instructions / 4178123626453464471 x1]; 4c2e8d4/PE/x86 [55 instructions / 5341803894337106697 x1].
type:.eq.M1K3M17K3M12: 4c2e8d4/ELF/x86 [48 instructions / 10263242420965979841 x1]; 4c2e8d4/PE/x86 [49 instructions / 14252954306763655565 x1].
type:.eq.M1K3M20: 4c2e8d4/ELF/x64 [15 instructions / 12657074631956980931 x1]; 4c2e8d4/ELF/x86 [36 instructions / 9440249621339446734 x1]; 4c2e8d4/PE/x64 [15 instructions / 12657074631956980931 x1]; 4c2e8d4/PE/x86 [37 instructions / 16788567838520398410 x1].
type:.eq.M1K3M20[4M32]: 4c2e8d4/ELF/x64 [51 instructions / 15899643515893351402 x1]; 4c2e8d4/PE/x64 [51 instructions / 15899643515893351402 x1].
type:.eq.M1K3M24: 4c2e8d4/ELF/x64 [15 instructions / 7739587294901740329 x1]; 4c2e8d4/ELF/x86 [40 instructions / 16305704506184764536 x1].
type:.eq.M1K3M26K2M24: 4c2e8d4/ELF/x86 [70 instructions / 526218820915482741 x1]; 4c2e8d4/PE/x86 [71 instructions / 4045809664383662570 x1].
type:.eq.M1K3M29: 4c2e8d4/ELF/x86 [49 instructions / 16449547075955265765 x1]; 4c2e8d4/PE/x86 [50 instructions / 17980072324643213186 x1].
type:.eq.M1K3M4: 4c2e8d4/ELF/x64 [9 instructions / 12672722063967094838 x1]; 4c2e8d4/ELF/x86 [18 instructions / 7372013927647320708 x1]; 4c2e8d4/PE/x64 [9 instructions / 12672722063967094838 x1]; 4c2e8d4/PE/x86 [19 instructions / 17664176602741919704 x1].
type:.eq.M1K3M4EE: 4c2e8d4/ELF/x86 [44 instructions / 14101701297782083565 x1]; 4c2e8d4/PE/x86 [45 instructions / 797294312260456842 x1].
type:.eq.M1K3M5: 4c2e8d4/ELF/x64 [12 instructions / 18423716935030950766 x1]; 4c2e8d4/ELF/x86 [21 instructions / 10931919902750462307 x1]; 4c2e8d4/PE/x64 [12 instructions / 18423716935030950766 x1]; 4c2e8d4/PE/x86 [22 instructions / 13201830277087772200 x1].
type:.eq.M1K3M8: 4c2e8d4/ELF/x64 [9 instructions / 3555328449368072823 x1]; 4c2e8d4/ELF/x86 [22 instructions / 1896843709213794430 x1]; 4c2e8d4/PE/x64 [9 instructions / 3555328449368072823 x1]; 4c2e8d4/PE/x86 [23 instructions / 4054636545637511462 x1].
type:.eq.M1K3M8E: 4c2e8d4/ELF/x86 [36 instructions / 10967274757340094260 x1]; 4c2e8d4/PE/x86 [37 instructions / 12415576286882317879 x1].
type:.eq.M1K3M8K4M16: 4c2e8d4/ELF/x64 [15 instructions / 12582227223962776000 x1]; 4c2e8d4/PE/x64 [15 instructions / 12582227223962776000 x1].
type:.eq.M1K3S: 4c2e8d4/ELF/x86 [27 instructions / 15838250103820154978 x1]; 4c2e8d4/PE/x86 [28 instructions / 6815224971673712392 x1].
type:.eq.M1K3SE: 4c2e8d4/ELF/x86 [41 instructions / 4674159326978094895 x1].
type:.eq.M1K3SM4: 4c2e8d4/ELF/x86 [30 instructions / 15757002560571319107 x1]; 4c2e8d4/PE/x86 [31 instructions / 8221465030276157287 x1].
type:.eq.M1K3SM4I: 4c2e8d4/ELF/x86 [44 instructions / 16469068135525734231 x1]; 4c2e8d4/PE/x86 [45 instructions / 478022807494333952 x1].
type:.eq.M1K3SS: 4c2e8d4/ELF/x86 [42 instructions / 14534562264827432894 x1]; 4c2e8d4/PE/x86 [43 instructions / 10115337746888774233 x1].
type:.eq.M1K3SSM37K3M8: 4c2e8d4/ELF/x86 [120 instructions / 16842957891811192719 x1]; 4c2e8d4/PE/x86 [121 instructions / 14259632792812161396 x1].
type:.eq.M1K7I: 4c2e8d4/ELF/x64 [27 instructions / 17409539404456875815 x1]; 4c2e8d4/PE/x64 [27 instructions / 17409539404456875815 x1].
type:.eq.M1K7IM8: 4c2e8d4/ELF/x64 [37 instructions / 6240254036286182143 x1]; 4c2e8d4/PE/x64 [37 instructions / 6240254036286182143 x1].
type:.eq.M1K7M16: 4c2e8d4/ELF/x64 [13 instructions / 16059620463625289763 x1]; 4c2e8d4/PE/x64 [13 instructions / 16059620463625289763 x1].
type:.eq.M1K7M16E: 4c2e8d4/ELF/x64 [33 instructions / 17588789151329107607 x1]; 4c2e8d4/PE/x64 [33 instructions / 17588789151329107607 x1].
type:.eq.M1K7M24: 4c2e8d4/ELF/x64 [15 instructions / 2450729788796882604 x1]; 4c2e8d4/PE/x64 [15 instructions / 2450729788796882604 x1].
type:.eq.M1K7M25K3M12: 4c2e8d4/ELF/x64 [25 instructions / 3586702295138115755 x1]; 4c2e8d4/PE/x64 [25 instructions / 3586702295138115755 x1].
type:.eq.M1K7M30K2M24: 4c2e8d4/ELF/x64 [29 instructions / 12639914422921660269 x1]; 4c2e8d4/PE/x64 [29 instructions / 12639914422921660269 x1].
type:.eq.M1K7M44K4M9: 4c2e8d4/ELF/x64 [32 instructions / 6255570295995447539 x1]; 4c2e8d4/PE/x64 [32 instructions / 6255570295995447539 x1].
type:.eq.M1K7M8: 4c2e8d4/ELF/x64 [9 instructions / 1254152962661677331 x1]; 4c2e8d4/PE/x64 [9 instructions / 1254152962661677331 x1].
type:.eq.M1K7M8EE: 4c2e8d4/ELF/x64 [43 instructions / 18287848319831611830 x1]; 4c2e8d4/PE/x64 [43 instructions / 18287848319831611830 x1].
type:.eq.M1K7M8IIM24: 4c2e8d4/ELF/x64 [55 instructions / 7455517881545891910 x1]; 4c2e8d4/PE/x64 [55 instructions / 7455517881545891910 x1].
type:.eq.M1K7S: 4c2e8d4/ELF/x64 [25 instructions / 1611650318003447607 x1]; 4c2e8d4/PE/x64 [25 instructions / 1611650318003447607 x1].
type:.eq.M1K7SE: 4c2e8d4/ELF/x64 [38 instructions / 2352304807403976781 x1].
type:.eq.M1K7SM4: 4c2e8d4/ELF/x64 [28 instructions / 16236072713210097401 x1]; 4c2e8d4/PE/x64 [28 instructions / 16236072713210097401 x1].
type:.eq.M1K7SM4K4I: 4c2e8d4/ELF/x64 [41 instructions / 11144211345022793645 x1]; 4c2e8d4/PE/x64 [41 instructions / 11144211345022793645 x1].
type:.eq.M1K7SS: 4c2e8d4/ELF/x64 [40 instructions / 10811424713326356214 x1]; 4c2e8d4/PE/x64 [40 instructions / 10811424713326356214 x1].
type:.eq.M1K7SSM4K4M4K4M41K7M8: 4c2e8d4/ELF/x64 [66 instructions / 9780735977698825357 x1]; 4c2e8d4/PE/x64 [66 instructions / 9780735977698825357 x1].
type:.eq.M20: 4c2e8d4/ELF/x64 [12 instructions / 15767004974410028936 x1]; 4c2e8d4/PE/x64 [12 instructions / 15767004974410028936 x1].
type:.eq.M209K3M8: 4c2e8d4/ELF/x86 [30 instructions / 1109001959418694598 x1]; 4c2e8d4/PE/x86 [31 instructions / 10845885469189448464 x1].
type:.eq.M20IM1: 4c2e8d4/ELF/x86 [52 instructions / 4717058323454823945 x1]; 4c2e8d4/PE/x86 [53 instructions / 10243428277793035918 x1].
type:.eq.M20K4M16: 4c2e8d4/ELF/x64 [19 instructions / 9770341139721181135 x1]; 4c2e8d4/PE/x64 [19 instructions / 9770341139721181135 x1].
type:.eq.M20K4M26K6SM4K4M82: 4c2e8d4/ELF/x64 [58 instructions / 10013347383007922657 x1]; 4c2e8d4/PE/x64 [58 instructions / 10013347383007922657 x1].
type:.eq.M20K4M29K3M52K4M52: 4c2e8d4/PE/x64 [71 instructions / 2243958379691669861 x1].
type:.eq.M20K4M40: 4c2e8d4/ELF/x64 [29 instructions / 12276034522165273504 x1]; 4c2e8d4/PE/x64 [29 instructions / 12276034522165273504 x1].
type:.eq.M20K4M4K4M26K6SM4K4M26K6SM4K4M82: 4c2e8d4/ELF/x64 [93 instructions / 2981887572864239431 x1]; 4c2e8d4/PE/x64 [93 instructions / 2981887572864239431 x1].
type:.eq.M20K4M8: 4c2e8d4/ELF/x64 [15 instructions / 10779358991531175362 x1]; 4c2e8d4/PE/x64 [15 instructions / 10779358991531175362 x1].
type:.eq.M20SM1K3M8: 4c2e8d4/ELF/x86 [61 instructions / 12164089616970534794 x1]; 4c2e8d4/PE/x86 [62 instructions / 8430011355684918382 x1].
type:.eq.M217K7M16: 4c2e8d4/ELF/x64 [32 instructions / 9813570119831634438 x1]; 4c2e8d4/PE/x64 [32 instructions / 9813570119831634438 x1].
type:.eq.M21K3M17K3M45K3M25K3M26K2SM4: 4c2e8d4/ELF/x86 [189 instructions / 14365661741490736595 x1]; 4c2e8d4/PE/x86 [190 instructions / 17823638323126728140 x1].
type:.eq.M21K3M2K2M20: 4c2e8d4/ELF/x64 [24 instructions / 8272631834842371037 x1].
type:.eq.M21K3M32: 4c2e8d4/PE/x86 [74 instructions / 12662039683853322361 x1].
type:.eq.M22: 4c2e8d4/ELF/x86 [37 instructions / 4520015449284530640 x1]; 4c2e8d4/PE/x86 [38 instructions / 7210031648942285644 x1].
type:.eq.M22K2M22K2M8: 4c2e8d4/ELF/x86 [73 instructions / 208366242839284134 x1]; 4c2e8d4/PE/x86 [74 instructions / 16026003053337210236 x1].
type:.eq.M22K2M6: 4c2e8d4/ELF/x86 [45 instructions / 7933306956872192584 x1]; 4c2e8d4/PE/x86 [46 instructions / 13895061548719300496 x1].
type:.eq.M22K2M656412: 4c2e8d4/ELF/x64 [31 instructions / 3530946813328987026 x1]; 4c2e8d4/ELF/x86 [48 instructions / 10737424815937094465 x1]; 4c2e8d4/PE/x64 [31 instructions / 3530946813328987026 x1]; 4c2e8d4/PE/x86 [49 instructions / 17207740016206969228 x1].
type:.eq.M23K1M9: 4c2e8d4/ELF/x86 [51 instructions / 7864742764293024774 x1]; 4c2e8d4/PE/x86 [52 instructions / 8424532913285230689 x1].
type:.eq.M244K4M28K4M12K4M130K2M8K4M8: 4c2e8d4/PE/x64 [62 instructions / 2990459704841406884 x1].
type:.eq.M24E: 4c2e8d4/ELF/x64 [34 instructions / 16276721939380835671 x1]; 4c2e8d4/PE/x64 [34 instructions / 16276721939380835671 x1].
type:.eq.M24EM8: 4c2e8d4/ELF/x64 [43 instructions / 14760181509791392397 x1]; 4c2e8d4/PE/x64 [43 instructions / 14760181509791392397 x1].
type:.eq.M24I: 4c2e8d4/ELF/x64 [34 instructions / 16276721939380835671 x1]; 4c2e8d4/PE/x64 [34 instructions / 16276721939380835671 x1].
type:.eq.M24II: 4c2e8d4/ELF/x64 [47 instructions / 480918276745947089 x1]; 4c2e8d4/PE/x64 [47 instructions / 480918276745947089 x1].
type:.eq.M24IM1: 4c2e8d4/ELF/x64 [43 instructions / 10991688840812679305 x1]; 4c2e8d4/ELF/x86 [58 instructions / 16241792145832662924 x1]; 4c2e8d4/PE/x64 [43 instructions / 10991688840812679305 x1]; 4c2e8d4/PE/x86 [59 instructions / 4466537410117504476 x1].
type:.eq.M24IM4: 4c2e8d4/ELF/x86 [58 instructions / 7313894440931646248 x1]; 4c2e8d4/PE/x86 [59 instructions / 7588214858662516964 x1].
type:.eq.M24K8M40: 4c2e8d4/ELF/x64 [28 instructions / 14195861876388049622 x1]; 4c2e8d4/PE/x64 [28 instructions / 14195861876388049622 x1].
type:.eq.M24S: 4c2e8d4/ELF/x64 [33 instructions / 6975203540021603931 x1]; 4c2e8d4/ELF/x86 [51 instructions / 8016217696982522903 x1]; 4c2e8d4/PE/x64 [33 instructions / 6975203540021603931 x1]; 4c2e8d4/PE/x86 [52 instructions / 9800461989877268236 x1].
type:.eq.M24SM1K7M8: 4c2e8d4/ELF/x64 [40 instructions / 17544509024672275041 x1]; 4c2e8d4/PE/x64 [40 instructions / 17544509024672275041 x1].
type:.eq.M25K3M17K3M4K4M49K7M28K4M1K7M4K4M26K6SM8: 4c2e8d4/ELF/x64 [111 instructions / 11422765005638169497 x1]; 4c2e8d4/PE/x64 [111 instructions / 11422765005638169497 x1].
type:.eq.M25K3M53K3M45: 4c2e8d4/PE/x86 [158 instructions / 12516266396739811538 x1].
type:.eq.M25K3M53K3M45K3M25K3M53K3M45K3M28: 4c2e8d4/PE/x86 [337 instructions / 16409523452688754850 x1].
type:.eq.M25K7M20: 4c2e8d4/ELF/x64 [24 instructions / 11470363731910213181 x1]; 4c2e8d4/PE/x64 [24 instructions / 11470363731910213181 x1].
type:.eq.M25K7M26K6M26K2M8: 4c2e8d4/ELF/x64 [44 instructions / 12239536512992988837 x1]; 4c2e8d4/PE/x64 [44 instructions / 12239536512992988837 x1].
type:.eq.M25K7M616: 4c2e8d4/ELF/x64 [34 instructions / 12405518260098617258 x1]; 4c2e8d4/PE/x64 [34 instructions / 12405518260098617258 x1].
type:.eq.M26K2M10K2M4: 4c2e8d4/ELF/x86 [57 instructions / 9112381920944355612 x1]; 4c2e8d4/PE/x86 [58 instructions / 6437495062763332528 x1].
type:.eq.M26K2M10K2M5K3M9K3M8: 4c2e8d4/ELF/x86 [79 instructions / 13047001355634149019 x1]; 4c2e8d4/PE/x86 [80 instructions / 8504816027598154276 x1].
type:.eq.M26K2M18K2M33K7M2K6M9K3M10K2M1K7M8: 4c2e8d4/ELF/x64 [65 instructions / 1445272190048688334 x1]; 4c2e8d4/PE/x64 [65 instructions / 1445272190048688334 x1].
type:.eq.M26K2M6: 4c2e8d4/ELF/x64 [21 instructions / 13860835164552886744 x1]; 4c2e8d4/PE/x64 [21 instructions / 13860835164552886744 x1].
type:.eq.M26K2M84: 4c2e8d4/ELF/x64 [33 instructions / 7304468383263549284 x1]; 4c2e8d4/PE/x64 [33 instructions / 7304468383263549284 x1].
type:.eq.M26K2S: 4c2e8d4/ELF/x86 [54 instructions / 14809817689864327022 x1]; 4c2e8d4/PE/x86 [55 instructions / 11823937209205247611 x1].
type:.eq.M26K6M10K2M4: 4c2e8d4/ELF/x64 [24 instructions / 2161792121723470446 x1]; 4c2e8d4/PE/x64 [24 instructions / 2161792121723470446 x1].
type:.eq.M26K6M10K2M5K7M9K3M12: 4c2e8d4/ELF/x64 [41 instructions / 5986794458986487091 x1]; 4c2e8d4/PE/x64 [41 instructions / 5986794458986487091 x1].
type:.eq.M26K6M26K2M8: 4c2e8d4/ELF/x64 [31 instructions / 17155916971967988228 x1]; 4c2e8d4/PE/x64 [31 instructions / 17155916971967988228 x1].
type:.eq.M26K6M32: 4c2e8d4/ELF/x64 [28 instructions / 3852733816762645368 x1]; 4c2e8d4/PE/x64 [28 instructions / 3852733816762645368 x1].
type:.eq.M276K4M48: 4c2e8d4/ELF/x64 [44 instructions / 10979389047112768444 x1]; 4c2e8d4/PE/x64 [44 instructions / 10979389047112768444 x1].
type:.eq.M28K4M25: 4c2e8d4/PE/x64 [29 instructions / 9977734259718415105 x1].
type:.eq.M28K4M4: 4c2e8d4/PE/x64 [19 instructions / 9662183128391759388 x1].
type:.eq.M28S: 4c2e8d4/PE/x86 [55 instructions / 499494203547703542 x1].
type:.eq.M29K3M17K3M45K3M25K3M26K2SM30K2SM5: 4c2e8d4/ELF/x86 [264 instructions / 4000595405970266644 x1]; 4c2e8d4/PE/x86 [265 instructions / 4715093706468020292 x1].
type:.eq.M29K3SS: 4c2e8d4/ELF/x86 [75 instructions / 13681147901747599028 x1]; 4c2e8d4/PE/x86 [76 instructions / 4798549268098736503 x1].
type:.eq.M2K2I: 4c2e8d4/ELF/x86 [27 instructions / 4962939025309852390 x1]; 4c2e8d4/PE/x86 [28 instructions / 6563612481906104580 x1].
type:.eq.M2K2M10: 4c2e8d4/ELF/x64 [12 instructions / 6772403076294835504 x1]; 4c2e8d4/ELF/x86 [27 instructions / 8126680650802011100 x1].
type:.eq.M2K2M12: 4c2e8d4/ELF/x64 [12 instructions / 12494109358469622119 x1]; 4c2e8d4/ELF/x86 [27 instructions / 12172359093845795883 x1]; 4c2e8d4/PE/x64 [12 instructions / 12494109358469622119 x1]; 4c2e8d4/PE/x86 [28 instructions / 6748255603795085918 x1].
type:.eq.M2K2M13: 4c2e8d4/ELF/x64 [12 instructions / 6989460958879284070 x1]; 4c2e8d4/ELF/x86 [31 instructions / 17399178007265402160 x1].
type:.eq.M2K2M14: 4c2e8d4/ELF/x64 [12 instructions / 2406935332100165177 x1]; 4c2e8d4/ELF/x86 [31 instructions / 9361727052482576221 x1].
type:.eq.M2K2M17: 4c2e8d4/ELF/x64 [15 instructions / 1141684315072191519 x1]; 4c2e8d4/ELF/x86 [36 instructions / 1101688320995040263 x1].
type:.eq.M2K2M19: 4c2e8d4/ELF/x64 [15 instructions / 17484326485286387995 x1]; 4c2e8d4/ELF/x86 [36 instructions / 7470507933625664166 x1].
type:.eq.M2K2M20: 4c2e8d4/ELF/x64 [15 instructions / 8031383309344628905 x1]; 4c2e8d4/ELF/x86 [36 instructions / 10368188943880570497 x1].
type:.eq.M2K2M22K2M20: 4c2e8d4/ELF/x86 [63 instructions / 18146347259823961177 x1]; 4c2e8d4/PE/x86 [64 instructions / 8584452859250890157 x1].
type:.eq.M2K2M23: 4c2e8d4/ELF/x64 [15 instructions / 9797570989231585964 x1]; 4c2e8d4/ELF/x86 [40 instructions / 13480909195884851160 x1].
type:.eq.M2K2M24: 4c2e8d4/ELF/x64 [15 instructions / 8986953664692023030 x1]; 4c2e8d4/ELF/x86 [40 instructions / 5133277279460315426 x1].
type:.eq.M2K2M28: 4c2e8d4/ELF/x64 [18 instructions / 17971628085700695665 x1]; 4c2e8d4/ELF/x86 [45 instructions / 8191713302616984600 x1].
type:.eq.M2K2M36: 4c2e8d4/ELF/x86 [54 instructions / 14773217456747570905 x1].
type:.eq.M2K2M4: 4c2e8d4/ELF/x64 [9 instructions / 7839956378543495923 x1]; 4c2e8d4/ELF/x86 [18 instructions / 4424722123768614729 x1]; 4c2e8d4/PE/x64 [9 instructions / 7839956378543495923 x1]; 4c2e8d4/PE/x86 [19 instructions / 11375695448108888938 x1].
type:.eq.M2K2M5: 4c2e8d4/ELF/x64 [12 instructions / 3312360150584361374 x1]; 4c2e8d4/ELF/x86 [21 instructions / 10747695346419163942 x1]; 4c2e8d4/PE/x64 [12 instructions / 3312360150584361374 x1]; 4c2e8d4/PE/x86 [22 instructions / 14771247544605718206 x1].
type:.eq.M2K2M5K3M10: 4c2e8d4/ELF/x86 [33 instructions / 16422778741643232800 x1]; 4c2e8d4/PE/x86 [34 instructions / 8441289295896994244 x1].
type:.eq.M2K2M5K3M8: 4c2e8d4/ELF/x64 [15 instructions / 5828704642849082736 x1]; 4c2e8d4/ELF/x86 [28 instructions / 922958096111494183 x1].
type:.eq.M2K2M7: 4c2e8d4/ELF/x64 [12 instructions / 11107611709770395101 x1]; 4c2e8d4/ELF/x86 [21 instructions / 8068186071302113242 x1].
type:.eq.M2K2M77K3M4: 4c2e8d4/ELF/x86 [31 instructions / 12727482746814758813 x1].
type:.eq.M2K2M77K7M8: 4c2e8d4/ELF/x64 [33 instructions / 11981929631721814726 x1].
type:.eq.M2K2M7K1M8: 4c2e8d4/ELF/x64 [15 instructions / 12931562375103554637 x1]; 4c2e8d4/ELF/x86 [28 instructions / 2414355051976887118 x1].
type:.eq.M2K2M8: 4c2e8d4/ELF/x64 [9 instructions / 14326282498659388479 x1]; 4c2e8d4/ELF/x86 [22 instructions / 3974655129759526560 x1]; 4c2e8d4/PE/x64 [9 instructions / 14326282498659388479 x1]; 4c2e8d4/PE/x86 [23 instructions / 9249426447507932724 x1].
type:.eq.M2K2M8K4M8: 4c2e8d4/ELF/x64 [12 instructions / 7639409781684915419 x1]; 4c2e8d4/PE/x64 [12 instructions / 7639409781684915419 x1].
type:.eq.M2K2M9: 4c2e8d4/ELF/x64 [13 instructions / 1813578407319381710 x1]; 4c2e8d4/ELF/x86 [27 instructions / 12173740222139436363 x1].
type:.eq.M2K2S: 4c2e8d4/ELF/x86 [27 instructions / 3298470455917944249 x1]; 4c2e8d4/PE/x86 [28 instructions / 5798072058599793528 x1].
type:.eq.M2K2SM7: 4c2e8d4/ELF/x86 [33 instructions / 12818011418800493321 x1].
type:.eq.M2K2SM8: 4c2e8d4/ELF/x86 [40 instructions / 6633922352389459767 x1]; 4c2e8d4/PE/x86 [41 instructions / 15911643388703576805 x1].
type:.eq.M2K6I: 4c2e8d4/ELF/x64 [28 instructions / 14332387118625293604 x1]; 4c2e8d4/PE/x64 [28 instructions / 14332387118625293604 x1].
type:.eq.M2K6M26K6M24: 4c2e8d4/ELF/x64 [28 instructions / 4982399155647970461 x1]; 4c2e8d4/PE/x64 [28 instructions / 4982399155647970461 x1].
type:.eq.M2K6M40: 4c2e8d4/ELF/x64 [21 instructions / 2025252537638190322 x1].
type:.eq.M2K6M9K3M10: 4c2e8d4/ELF/x64 [19 instructions / 4445168834328455850 x1]; 4c2e8d4/PE/x64 [19 instructions / 4445168834328455850 x1].
type:.eq.M2K6S: 4c2e8d4/ELF/x64 [26 instructions / 10174184158786222862 x1]; 4c2e8d4/PE/x64 [26 instructions / 10174184158786222862 x1].
type:.eq.M2K6SM16: 4c2e8d4/ELF/x64 [33 instructions / 15090126375094786521 x1]; 4c2e8d4/PE/x64 [33 instructions / 15090126375094786521 x1].
type:.eq.M2K6SM7: 4c2e8d4/ELF/x64 [33 instructions / 4772181750901970592 x1].
type:.eq.M300K4M16: 4c2e8d4/ELF/x64 [32 instructions / 3856652723269147077 x1]; 4c2e8d4/PE/x64 [32 instructions / 3856652723269147077 x1].
type:.eq.M30K2M64: 4c2e8d4/ELF/x86 [118 instructions / 10557787918460983823 x1]; 4c2e8d4/PE/x86 [119 instructions / 12576901731882493095 x1].
type:.eq.M31K1M9: 4c2e8d4/ELF/x64 [21 instructions / 9316357569447908143 x1]; 4c2e8d4/PE/x64 [21 instructions / 9316357569447908143 x1].
type:.eq.M32: 4c2e8d4/ELF/x64 [15 instructions / 7710033937733822100 x1]; 4c2e8d4/ELF/x86 [46 instructions / 17953982809924574184 x1]; 4c2e8d4/PE/x64 [15 instructions / 7710033937733822100 x1]; 4c2e8d4/PE/x86 [47 instructions / 1226058745807719467 x1].
type:.eq.M32IM1: 4c2e8d4/ELF/x64 [48 instructions / 11524234833286122561 x1]; 4c2e8d4/PE/x64 [48 instructions / 11524234833286122561 x1].
type:.eq.M32ISM8: 4c2e8d4/ELF/x86 [87 instructions / 10787500281629303065 x1]; 4c2e8d4/PE/x86 [88 instructions / 2107946185427538630 x1].
type:.eq.M33K3FFK4M9K7M28K4M24FF: 4c2e8d4/ELF/x64 [70 instructions / 15689669760126154946 x1]; 4c2e8d4/PE/x64 [70 instructions / 15689669760126154946 x1].
type:.eq.M33K3FFM9K3M52FF: 4c2e8d4/ELF/x86 [141 instructions / 16893294505987557641 x1]; 4c2e8d4/PE/x86 [142 instructions / 10517850155036926042 x1].
type:.eq.M33K7M48: 4c2e8d4/PE/x64 [38 instructions / 3691096723311088671 x1].
type:.eq.M34K2SM70: 4c2e8d4/ELF/x86 [75 instructions / 1210662203901695233 x1]; 4c2e8d4/PE/x86 [76 instructions / 14580589614322467251 x1].
type:.eq.M356K4M12K4M32IM2K2M193K3M12EM8: 4c2e8d4/ELF/x86 [132 instructions / 6682659144772556861 x1]; 4c2e8d4/PE/x86 [133 instructions / 10785755116072915562 x1].
type:.eq.M358K2M12: 4c2e8d4/PE/x86 [36 instructions / 8709676185561147698 x1].
type:.eq.M36K4M16IM8I: 4c2e8d4/ELF/x64 [63 instructions / 13188880631857048385 x1]; 4c2e8d4/PE/x64 [63 instructions / 13188880631857048385 x1].
type:.eq.M36K4M24: 4c2e8d4/ELF/x64 [28 instructions / 16106830293501776355 x1]; 4c2e8d4/PE/x64 [28 instructions / 16106830293501776355 x1].
type:.eq.M36K4M8: 4c2e8d4/ELF/x64 [21 instructions / 12368153129690767935 x1]; 4c2e8d4/PE/x64 [21 instructions / 12368153129690767935 x1].
type:.eq.M38K2M8: 4c2e8d4/ELF/x86 [64 instructions / 17425172544107245876 x1]; 4c2e8d4/PE/x86 [65 instructions / 17558445269113562025 x1].
type:.eq.M38K2SM26K2SM70: 4c2e8d4/ELF/x86 [126 instructions / 11114198285226426775 x1]; 4c2e8d4/PE/x86 [127 instructions / 1621339909295462461 x1].
type:.eq.M39K1M9K3SII: 4c2e8d4/ELF/x86 [109 instructions / 13421442834939991545 x1].
type:.eq.M39K1SM8: 4c2e8d4/ELF/x86 [80 instructions / 12805921539111563265 x1].
type:.eq.M3K1M11K1M4: 4c2e8d4/ELF/x86 [33 instructions / 8121354193543794775 x1]; 4c2e8d4/PE/x86 [34 instructions / 10961876819749536751 x1].
type:.eq.M3K1M12: 4c2e8d4/ELF/x64 [15 instructions / 4058227593194685405 x1]; 4c2e8d4/ELF/x86 [30 instructions / 14808921764009926854 x1]; 4c2e8d4/PE/x64 [15 instructions / 4058227593194685405 x1]; 4c2e8d4/PE/x86 [31 instructions / 6526768364014470086 x1].
type:.eq.M3K1M16: 4c2e8d4/ELF/x64 [15 instructions / 13786941678182006528 x1]; 4c2e8d4/ELF/x86 [34 instructions / 15791044303103233217 x1]; 4c2e8d4/PE/x64 [15 instructions / 13786941678182006528 x1]; 4c2e8d4/PE/x86 [35 instructions / 15890528588193982557 x1].
type:.eq.M3K1M18: 4c2e8d4/ELF/x86 [39 instructions / 13163458669214440318 x1]; 4c2e8d4/PE/x86 [40 instructions / 8382630473803254084 x1].
type:.eq.M3K1M24: 4c2e8d4/ELF/x64 [19 instructions / 9729213632676379039 x1]; 4c2e8d4/ELF/x86 [43 instructions / 17872210847338195892 x1].
type:.eq.M3K1M27: 4c2e8d4/ELF/x64 [22 instructions / 5476753647681995002 x1]; 4c2e8d4/ELF/x86 [48 instructions / 1350192571217486577 x1].
type:.eq.M3K1M28: 4c2e8d4/ELF/x64 [22 instructions / 3108355427084047638 x1]; 4c2e8d4/ELF/x86 [48 instructions / 10859457690046038667 x1].
type:.eq.M3K1M4: 4c2e8d4/ELF/x64 [12 instructions / 16619475997085736251 x1]; 4c2e8d4/ELF/x86 [21 instructions / 735042039036833683 x1]; 4c2e8d4/PE/x64 [12 instructions / 16619475997085736251 x1]; 4c2e8d4/PE/x86 [22 instructions / 5046266196769010730 x1].
type:.eq.M3K1M5: 4c2e8d4/ELF/x64 [15 instructions / 5988429501529356797 x1]; 4c2e8d4/ELF/x86 [24 instructions / 8668833354135816685 x1].
type:.eq.M3K1M8: 4c2e8d4/ELF/x64 [13 instructions / 4980497404202493145 x1]; 4c2e8d4/ELF/x86 [25 instructions / 15624620535178664240 x1]; 4c2e8d4/PE/x64 [13 instructions / 4980497404202493145 x1]; 4c2e8d4/PE/x86 [26 instructions / 13985931722264792537 x1].
type:.eq.M3K1M8K4SM4: 4c2e8d4/ELF/x64 [35 instructions / 13862720941705468835 x1]; 4c2e8d4/PE/x64 [35 instructions / 13862720941705468835 x1].
type:.eq.M3K1M8SM4: 4c2e8d4/ELF/x86 [42 instructions / 16605336659931604509 x1]; 4c2e8d4/PE/x86 [43 instructions / 13876593562450377607 x1].
type:.eq.M3K5M15K1M8: 4c2e8d4/ELF/x64 [19 instructions / 6188455187386532129 x1]; 4c2e8d4/PE/x64 [19 instructions / 6188455187386532129 x1].
type:.eq.M3K5M24: 4c2e8d4/ELF/x64 [19 instructions / 1355623858715667790 x1].
type:.eq.M3K5M34: 4c2e8d4/ELF/x64 [25 instructions / 5272352592901857010 x1]; 4c2e8d4/PE/x64 [25 instructions / 5272352592901857010 x1].
type:.eq.M40IM8: 4c2e8d4/ELF/x64 [50 instructions / 5001064166022366804 x1]; 4c2e8d4/PE/x64 [50 instructions / 5001064166022366804 x1].
type:.eq.M40IM8I: 4c2e8d4/ELF/x86 [92 instructions / 7295559048490024070 x1]; 4c2e8d4/PE/x86 [93 instructions / 12106822296781932953 x1].
type:.eq.M40ISM4K4M8: 4c2e8d4/ELF/x64 [58 instructions / 13971609422273402108 x1]; 4c2e8d4/PE/x64 [58 instructions / 13971609422273402108 x1].
type:.eq.M40S: 4c2e8d4/PE/x64 [39 instructions / 18322926558474360618 x1].
type:.eq.M40SM25: 4c2e8d4/ELF/x86 [107 instructions / 2442773428723223124 x1]; 4c2e8d4/PE/x86 [108 instructions / 13495240322873561246 x1].
type:.eq.M40SM25K3M28ISM16: 4c2e8d4/ELF/x86 [207 instructions / 7113389383485482425 x1]; 4c2e8d4/PE/x86 [208 instructions / 10551142224979707970 x1].
type:.eq.M40SM25K3S: 4c2e8d4/ELF/x86 [126 instructions / 1073387965438823197 x1]; 4c2e8d4/PE/x86 [127 instructions / 9437942165069661044 x1].
type:.eq.M40SM25K3SI: 4c2e8d4/ELF/x86 [140 instructions / 1271861772001472292 x1]; 4c2e8d4/PE/x86 [141 instructions / 13742655511576488972 x1].
type:.eq.M40SM25K3SM4: 4c2e8d4/ELF/x86 [129 instructions / 8524819188695577470 x1]; 4c2e8d4/PE/x86 [130 instructions / 7898815310246917760 x1].
type:.eq.M41K3M17K3M4K4M49K7M28K4M1K7M4K4M26K6SM12K4M26K6SM5: 4c2e8d4/ELF/x64 [168 instructions / 381124627556315657 x1]; 4c2e8d4/PE/x64 [168 instructions / 381124627556315657 x1].
type:.eq.M41K7M81K7M65: 4c2e8d4/PE/x64 [50 instructions / 7181947347592795469 x1].
type:.eq.M41K7M81K7M65K7M41K7M81K7M65K7M28: 4c2e8d4/PE/x64 [112 instructions / 1457773131679467057 x1].
type:.eq.M41K7SS: 4c2e8d4/ELF/x64 [56 instructions / 7758518386868982388 x1]; 4c2e8d4/PE/x64 [56 instructions / 7758518386868982388 x1].
type:.eq.M42K1M1: 4c2e8d4/ELF/x64 [24 instructions / 1171064313943610287 x1]; 4c2e8d4/ELF/x86 [63 instructions / 16313560315108939802 x1]; 4c2e8d4/PE/x64 [24 instructions / 1171064313943610287 x1]; 4c2e8d4/PE/x86 [64 instructions / 9617382661739318361 x1].
type:.eq.M44K4M17: 4c2e8d4/ELF/x64 [31 instructions / 17053236580087636965 x1]; 4c2e8d4/PE/x64 [31 instructions / 17053236580087636965 x1].
type:.eq.M44K4M8: 4c2e8d4/PE/x64 [24 instructions / 11561916612920570572 x1].
type:.eq.M45K3M4: 4c2e8d4/ELF/x86 [69 instructions / 5196145178166584104 x1]; 4c2e8d4/PE/x86 [70 instructions / 7737445759702395632 x1].
type:.eq.M48S: 4c2e8d4/ELF/x64 [43 instructions / 1114091875193847203 x1]; 4c2e8d4/PE/x64 [43 instructions / 1114091875193847203 x1].
type:.eq.M48SM29: 4c2e8d4/ELF/x64 [56 instructions / 12725227911439652345 x1]; 4c2e8d4/PE/x64 [56 instructions / 12725227911439652345 x1].
type:.eq.M48SM29K3M32ISM28: 4c2e8d4/ELF/x64 [107 instructions / 2416186389258025734 x1]; 4c2e8d4/PE/x64 [107 instructions / 2416186389258025734 x1].
type:.eq.M48SM29K3S: 4c2e8d4/ELF/x64 [66 instructions / 7139283228693741810 x1]; 4c2e8d4/PE/x64 [66 instructions / 7139283228693741810 x1].
type:.eq.M48SM29K3SI: 4c2e8d4/ELF/x64 [79 instructions / 7682834714456273974 x1]; 4c2e8d4/PE/x64 [79 instructions / 7682834714456273974 x1].
type:.eq.M48SM29K3SM8: 4c2e8d4/ELF/x64 [70 instructions / 3552210139080637939 x1]; 4c2e8d4/PE/x64 [70 instructions / 3552210139080637939 x1].
type:.eq.M492K4M1K3M20: 4c2e8d4/ELF/x86 [47 instructions / 5227236608244984284 x1]; 4c2e8d4/PE/x86 [48 instructions / 1013664978798723210 x1].
type:.eq.M492K4M1K3M5K3M16: 4c2e8d4/ELF/x86 [48 instructions / 2641003037549290162 x1]; 4c2e8d4/PE/x86 [49 instructions / 109900277060311490 x1].
type:.eq.M4EM4: 4c2e8d4/ELF/x86 [34 instructions / 501203736301344696 x1]; 4c2e8d4/PE/x86 [35 instructions / 4235040600412484772 x1].
type:.eq.M4I: 4c2e8d4/ELF/x86 [27 instructions / 14938944928051921969 x1]; 4c2e8d4/PE/x86 [28 instructions / 2066675420980254107 x1].
type:.eq.M4IIM8: 4c2e8d4/ELF/x86 [52 instructions / 13977925468256089841 x1]; 4c2e8d4/PE/x86 [53 instructions / 14977992267809322921 x1].
type:.eq.M4IM16: 4c2e8d4/ELF/x86 [47 instructions / 10873017566260838115 x1].
type:.eq.M4IM20: 4c2e8d4/ELF/x86 [52 instructions / 17313317379831400382 x1]; 4c2e8d4/PE/x86 [53 instructions / 15884759696793965107 x1].
type:.eq.M4IM3K1M16: 4c2e8d4/ELF/x86 [53 instructions / 7297300054026004682 x1]; 4c2e8d4/PE/x86 [54 instructions / 12976592857252850962 x1].
type:.eq.M4IM4: 4c2e8d4/ELF/x86 [34 instructions / 501203736301344696 x1]; 4c2e8d4/PE/x86 [35 instructions / 4235040600412484772 x1].
type:.eq.M4ISM16S: 4c2e8d4/ELF/x86 [82 instructions / 3411940708091655204 x1]; 4c2e8d4/PE/x86 [83 instructions / 16355938118100125554 x1].
type:.eq.M4K4EM8: 4c2e8d4/ELF/x64 [36 instructions / 7198436229412828608 x1]; 4c2e8d4/PE/x64 [36 instructions / 7198436229412828608 x1].
type:.eq.M4K4I: 4c2e8d4/ELF/x64 [27 instructions / 628694535491055094 x1]; 4c2e8d4/PE/x64 [27 instructions / 628694535491055094 x1].
type:.eq.M4K4IM3K5M24: 4c2e8d4/ELF/x64 [49 instructions / 17768499316937586513 x1]; 4c2e8d4/PE/x64 [49 instructions / 17768499316937586513 x1].
type:.eq.M4K4M12: 4c2e8d4/ELF/x86 [27 instructions / 1127386493101270194 x1]; 4c2e8d4/PE/x64 [12 instructions / 2617164785488391463 x1]; 4c2e8d4/PE/x86 [28 instructions / 12849868117158357565 x1].
type:.eq.M4K4M1232: 4c2e8d4/ELF/x64 [23 instructions / 11822146935198842925 x1]; 4c2e8d4/PE/x64 [23 instructions / 11822146935198842925 x1].
type:.eq.M4K4M12K4M28: 4c2e8d4/PE/x64 [25 instructions / 1900330378290717665 x1].
type:.eq.M4K4M12K4M29K3M88: 4c2e8d4/PE/x86 [73 instructions / 12343739432201685523 x1].
type:.eq.M4K4M12K4M8: 4c2e8d4/ELF/x64 [15 instructions / 9544647367834639080 x1]; 4c2e8d4/ELF/x86 [34 instructions / 17107595484567056965 x1]; 4c2e8d4/PE/x64 [15 instructions / 9544647367834639080 x1]; 4c2e8d4/PE/x86 [35 instructions / 16438805132830613376 x1].
type:.eq.M4K4M16: 4c2e8d4/PE/x64 [12 instructions / 11628263894614320574 x1].
type:.eq.M4K4M2122K6M2720: 4c2e8d4/ELF/x64 [33 instructions / 682644655015465753 x1]; 4c2e8d4/PE/x64 [33 instructions / 682644655015465753 x1].
type:.eq.M4K4M24: 4c2e8d4/ELF/x64 [15 instructions / 8104489038262511882 x1]; 4c2e8d4/PE/x64 [15 instructions / 8104489038262511882 x1].
type:.eq.M4K4M25: 4c2e8d4/ELF/x64 [19 instructions / 10522426516582625051 x1]; 4c2e8d4/PE/x64 [19 instructions / 10522426516582625051 x1].
type:.eq.M4K4M26K6S: 4c2e8d4/ELF/x64 [37 instructions / 13853658052348240041 x1]; 4c2e8d4/PE/x64 [37 instructions / 13853658052348240041 x1].
type:.eq.M4K4M32: 4c2e8d4/ELF/x64 [19 instructions / 15493037161137812420 x1]; 4c2e8d4/PE/x64 [19 instructions / 15493037161137812420 x1].
type:.eq.M4K4M324K4M68K4M32IM2K6M52K4M177K7M24EM12: 4c2e8d4/ELF/x64 [141 instructions / 470670865477752396 x1]; 4c2e8d4/PE/x64 [141 instructions / 470670865477752396 x1].
type:.eq.M4K4M34: 4c2e8d4/ELF/x64 [22 instructions / 16045292779549374075 x1]; 4c2e8d4/PE/x64 [22 instructions / 16045292779549374075 x1].
type:.eq.M4K4M48: 4c2e8d4/ELF/x64 [25 instructions / 14132439210101195505 x1]; 4c2e8d4/PE/x64 [25 instructions / 14132439210101195505 x1].
type:.eq.M4K4M52K4M17K7M8: 4c2e8d4/ELF/x64 [42 instructions / 12178305798658527314 x1]; 4c2e8d4/PE/x64 [42 instructions / 12178305798658527314 x1].
type:.eq.M4K4M8: 4c2e8d4/ELF/x64 [9 instructions / 13767068821182356926 x1]; 4c2e8d4/PE/x64 [9 instructions / 13767068821182356926 x1].
type:.eq.M4K4M8SSM8: 4c2e8d4/ELF/x64 [44 instructions / 531927366851121924 x1]; 4c2e8d4/PE/x64 [44 instructions / 531927366851121924 x1].
type:.eq.M4K4S: 4c2e8d4/ELF/x64 [26 instructions / 3113664805051790696 x1]; 4c2e8d4/PE/x64 [26 instructions / 3113664805051790696 x1].
type:.eq.M4K4SM33: 4c2e8d4/ELF/x64 [41 instructions / 7868102509716172932 x1]; 4c2e8d4/PE/x64 [41 instructions / 7868102509716172932 x1].
type:.eq.M4K4SS: 4c2e8d4/ELF/x64 [40 instructions / 3539718378696113727 x1]; 4c2e8d4/PE/x64 [40 instructions / 3539718378696113727 x1].
type:.eq.M4S: 4c2e8d4/ELF/x86 [27 instructions / 16308967205004002280 x1]; 4c2e8d4/PE/x86 [28 instructions / 414303372825323255 x1].
type:.eq.M4SE: 4c2e8d4/ELF/x86 [41 instructions / 18145485553654764751 x1]; 4c2e8d4/PE/x86 [42 instructions / 1466498984539731537 x1].
type:.eq.M4SM12: 4c2e8d4/ELF/x86 [43 instructions / 9205992399469144610 x1].
type:.eq.M4SM1K3M12: 4c2e8d4/ELF/x86 [46 instructions / 124931860040583439 x1]; 4c2e8d4/PE/x86 [47 instructions / 9986799868102790501 x1].
type:.eq.M4SM2: 4c2e8d4/PE/x86 [31 instructions / 9968435975402811234 x1].
type:.eq.M4SM29: 4c2e8d4/ELF/x86 [79 instructions / 7049493172420993839 x1]; 4c2e8d4/PE/x86 [80 instructions / 7554687292645048719 x1].
type:.eq.M4SM4: 4c2e8d4/PE/x86 [31 instructions / 16395767543393179430 x1].
type:.eq.M4SM4SM20K4I: 4c2e8d4/ELF/x86 [88 instructions / 9849883608464817152 x1]; 4c2e8d4/PE/x86 [89 instructions / 17849756839514417089 x1].
type:.eq.M4SS: 4c2e8d4/ELF/x86 [42 instructions / 3504853690539135218 x1]; 4c2e8d4/PE/x86 [43 instructions / 14270130713618426557 x1].
type:.eq.M4SSM2K2M20: 4c2e8d4/PE/x86 [75 instructions / 3233771977945284449 x1].
type:.eq.M4SSS: 4c2e8d4/ELF/x86 [57 instructions / 10925417125366855530 x1]; 4c2e8d4/PE/x86 [58 instructions / 10373969672076578054 x1].
type:.eq.M4SSSS: 4c2e8d4/ELF/x86 [72 instructions / 1632420943053571601 x1]; 4c2e8d4/PE/x86 [73 instructions / 5040232717988942922 x1].
type:.eq.M51K5M17K7SII: 4c2e8d4/ELF/x64 [79 instructions / 17237729330168109582 x1].
type:.eq.M51K5SM12: 4c2e8d4/ELF/x64 [52 instructions / 12405113558983849298 x1].
type:.eq.M52K4M26K6SM4K4M50: 4c2e8d4/ELF/x64 [85 instructions / 10052672198142839885 x1]; 4c2e8d4/PE/x64 [85 instructions / 10052672198142839885 x1].
type:.eq.M52K4M26K6SM5: 4c2e8d4/ELF/x64 [66 instructions / 12354636889886325422 x1]; 4c2e8d4/PE/x64 [66 instructions / 12354636889886325422 x1].
type:.eq.M52K4M9: 4c2e8d4/ELF/x64 [31 instructions / 12947457012635209158 x1]; 4c2e8d4/PE/x64 [31 instructions / 12947457012635209158 x1].
type:.eq.M53K3M1: 4c2e8d4/ELF/x86 [78 instructions / 9965690776018469918 x1]; 4c2e8d4/PE/x86 [79 instructions / 3579151990129115458 x1].
type:.eq.M53K3M4: 4c2e8d4/ELF/x86 [78 instructions / 16006101756992943043 x1]; 4c2e8d4/PE/x86 [79 instructions / 11521011908459909993 x1].
type:.eq.M54K2M104: 4c2e8d4/ELF/x64 [43 instructions / 15510451024736384372 x1]; 4c2e8d4/PE/x64 [43 instructions / 15510451024736384372 x1].
type:.eq.M56IM4: 4c2e8d4/ELF/x86 [94 instructions / 12543925854219249966 x1]; 4c2e8d4/PE/x86 [95 instructions / 8311820391824994566 x1].
type:.eq.M57K3M25K3M5K3M5K3M20GGM16GGGGGM66K2M10K2M9: 4c2e8d4/ELF/x86 [231 instructions / 1974402903761967166 x1]; 4c2e8d4/PE/x86 [232 instructions / 7433019055459670313 x1].
type:.eq.M58K2SM46: 4c2e8d4/ELF/x86 [162 instructions / 3916674120496763718 x1]; 4c2e8d4/PE/x86 [163 instructions / 409119924473607867 x1].
type:.eq.M58K2SM5: 4c2e8d4/ELF/x86 [96 instructions / 5769723075288020469 x1]; 4c2e8d4/PE/x86 [97 instructions / 11041011974741806124 x1].
type:.eq.M5K1M10: 4c2e8d4/ELF/x86 [30 instructions / 7046382882150430792 x1]; 4c2e8d4/PE/x86 [31 instructions / 8255251887470055284 x1].
type:.eq.M5K3IM12: 4c2e8d4/ELF/x86 [46 instructions / 15275160448046255080 x1]; 4c2e8d4/PE/x86 [47 instructions / 13263155624218356926 x1].
type:.eq.M5K3IM4K4M8: 4c2e8d4/ELF/x64 [43 instructions / 9614433737448525250 x1]; 4c2e8d4/PE/x64 [43 instructions / 9614433737448525250 x1].
type:.eq.M5K3M24: 4c2e8d4/ELF/x86 [43 instructions / 14950236500991930971 x1]; 4c2e8d4/PE/x86 [44 instructions / 9803157666016284906 x1].
type:.eq.M5K3M28: 4c2e8d4/ELF/x64 [22 instructions / 17903226584642384764 x1]; 4c2e8d4/PE/x64 [22 instructions / 17903226584642384764 x1].
type:.eq.M5K3M36II: 4c2e8d4/ELF/x86 [83 instructions / 7023240979600629248 x1]; 4c2e8d4/PE/x86 [84 instructions / 8525069901272683205 x1].
type:.eq.M5K3M4: 4c2e8d4/ELF/x86 [21 instructions / 16366077244389565626 x1]; 4c2e8d4/PE/x86 [22 instructions / 18039201430026700649 x1].
type:.eq.M5K3M41K3M41K3SSM1K3SSM1: 4c2e8d4/ELF/x86 [177 instructions / 14760392794037150304 x1]; 4c2e8d4/PE/x86 [178 instructions / 1699661551558551092 x1].
type:.eq.M5K3M49K7M49K7SSM1K7SSM1: 4c2e8d4/ELF/x64 [126 instructions / 9833009599507170149 x1]; 4c2e8d4/PE/x64 [126 instructions / 9833009599507170149 x1].
type:.eq.M5K3M8: 4c2e8d4/ELF/x64 [12 instructions / 4523273915253750936 x1]; 4c2e8d4/ELF/x86 [25 instructions / 11703339445794490669 x1]; 4c2e8d4/PE/x64 [12 instructions / 4523273915253750936 x1]; 4c2e8d4/PE/x86 [26 instructions / 1415717884505028359 x1].
type:.eq.M5K3SM4I: 4c2e8d4/ELF/x86 [47 instructions / 4786296071374772093 x1]; 4c2e8d4/PE/x86 [48 instructions / 6752263183151206580 x1].
type:.eq.M60K4M9K7M1: 4c2e8d4/ELF/x64 [38 instructions / 6009289376353150610 x1]; 4c2e8d4/PE/x64 [38 instructions / 6009289376353150610 x1].
type:.eq.M646K2M262144: 4c2e8d4/ELF/x86 [30 instructions / 13653768820118659122 x1]; 4c2e8d4/PE/x86 [31 instructions / 7479746218277476932 x1].
type:.eq.M650K2M262144: 4c2e8d4/ELF/x64 [30 instructions / 4650834092162068616 x1]; 4c2e8d4/PE/x64 [30 instructions / 4650834092162068616 x1].
type:.eq.M69K3M45K3M16I: 4c2e8d4/ELF/x86 [105 instructions / 1186025349799916246 x1]; 4c2e8d4/PE/x86 [106 instructions / 14034279912046790427 x1].
type:.eq.M6K2M12: 4c2e8d4/ELF/x64 [15 instructions / 10532745892926456108 x1]; 4c2e8d4/ELF/x86 [30 instructions / 17618468856417105582 x1].
type:.eq.M6K2M4: 4c2e8d4/ELF/x64 [12 instructions / 453556615867370799 x1]; 4c2e8d4/ELF/x86 [21 instructions / 11668286787579065966 x1]; 4c2e8d4/PE/x64 [12 instructions / 453556615867370799 x1]; 4c2e8d4/PE/x86 [22 instructions / 14077089365288195377 x1].
type:.eq.M6K2M8: 4c2e8d4/ELF/x64 [12 instructions / 2172071201211660494 x1]; 4c2e8d4/ELF/x86 [25 instructions / 6054908760995330354 x1]; 4c2e8d4/PE/x64 [12 instructions / 2172071201211660494 x1].
type:.eq.M6K2M8IM8: 4c2e8d4/ELF/x86 [50 instructions / 17563364431012279231 x1]; 4c2e8d4/PE/x86 [51 instructions / 15061835370625292808 x1].
type:.eq.M72IM4: 4c2e8d4/ELF/x86 [40 instructions / 15296780124127328937 x1]; 4c2e8d4/PE/x86 [41 instructions / 8981233217789699105 x1].
type:.eq.M761K3M20: 4c2e8d4/ELF/x64 [36 instructions / 9674772468046083305 x1]; 4c2e8d4/PE/x64 [36 instructions / 9674772468046083305 x1].
type:.eq.M761K3M5K7M16: 4c2e8d4/ELF/x64 [40 instructions / 12023436368133742932 x1]; 4c2e8d4/PE/x64 [40 instructions / 12023436368133742932 x1].
type:.eq.M7K1M16: 4c2e8d4/ELF/x86 [34 instructions / 10662993358454481309 x1]; 4c2e8d4/PE/x86 [35 instructions / 15141211002925522808 x1].
type:.eq.M7K1M2: 4c2e8d4/ELF/x64 [12 instructions / 12936376155074099273 x1]; 4c2e8d4/ELF/x86 [21 instructions / 14546794407042974144 x1]; 4c2e8d4/PE/x64 [12 instructions / 12936376155074099273 x1]; 4c2e8d4/PE/x86 [22 instructions / 3312191111863853700 x1].
type:.eq.M7K1M24: 4c2e8d4/ELF/x64 [19 instructions / 13004316881908855118 x1]; 4c2e8d4/PE/x64 [19 instructions / 13004316881908855118 x1].
type:.eq.M7K1M5K3M24: 4c2e8d4/ELF/x86 [49 instructions / 8147508586881559575 x1]; 4c2e8d4/PE/x86 [50 instructions / 4490020887635108750 x1].
type:.eq.M7K1M8: 4c2e8d4/ELF/x86 [25 instructions / 16201322357092331990 x1]; 4c2e8d4/PE/x86 [26 instructions / 441271239465519513 x1].
type:.eq.M7K1M9: 4c2e8d4/ELF/x64 [15 instructions / 2074508946027250355 x1]; 4c2e8d4/ELF/x86 [30 instructions / 13699550173569363704 x1].
type:.eq.M81K7M25K7M9K3M5K3M8K4M16GGM16GGGGGM4K4M66K6M10K2M9: 4c2e8d4/ELF/x64 [138 instructions / 2639283028262658507 x1]; 4c2e8d4/PE/x64 [138 instructions / 2639283028262658507 x1].
type:.eq.M84K4M16: 4c2e8d4/ELF/x64 [32 instructions / 3370065010466483810 x1]; 4c2e8d4/PE/x64 [32 instructions / 3370065010466483810 x1].
type:.eq.M88IM8: 4c2e8d4/ELF/x64 [38 instructions / 17539886177286417151 x1]; 4c2e8d4/PE/x64 [38 instructions / 17539886177286417151 x1].
type:.eq.M89K3M24K4M25K7M16I: 4c2e8d4/ELF/x64 [60 instructions / 10039197514197876606 x1]; 4c2e8d4/PE/x64 [60 instructions / 10039197514197876606 x1].
type:.eq.M8GM4GM40: 4c2e8d4/ELF/x86 [77 instructions / 14606292017760752129 x1]; 4c2e8d4/PE/x86 [78 instructions / 11549720743152721236 x1].
type:.eq.M8GM8GM48: 4c2e8d4/ELF/x64 [40 instructions / 2663285021647929059 x1]; 4c2e8d4/PE/x64 [40 instructions / 2663285021647929059 x1].
type:.eq.M8I: 4c2e8d4/ELF/x64 [28 instructions / 5919291975212290876 x1]; 4c2e8d4/ELF/x86 [33 instructions / 7529161204138778264 x1]; 4c2e8d4/PE/x64 [28 instructions / 5919291975212290876 x1]; 4c2e8d4/PE/x86 [34 instructions / 7417395952185799938 x1].
type:.eq.M8II: 4c2e8d4/ELF/x64 [42 instructions / 15531504533253187928 x1]; 4c2e8d4/ELF/x86 [47 instructions / 9683845216383595632 x1]; 4c2e8d4/PE/x64 [42 instructions / 15531504533253187928 x1]; 4c2e8d4/PE/x86 [48 instructions / 8810535136574117637 x1].
type:.eq.M8IIM1033K3M28: 4c2e8d4/ELF/x86 [92 instructions / 8452850916984989365 x1]; 4c2e8d4/PE/x86 [93 instructions / 13318144264766148577 x1].
type:.eq.M8IIM1033K7M32: 4c2e8d4/ELF/x64 [66 instructions / 14509901815505814942 x1]; 4c2e8d4/PE/x64 [66 instructions / 14509901815505814942 x1].
type:.eq.M8IIM30K2SM26K2SM4: 4c2e8d4/ELF/x86 [157 instructions / 9582282059002480290 x1]; 4c2e8d4/PE/x86 [158 instructions / 17592718426491173802 x1].
type:.eq.M8IIM8: 4c2e8d4/ELF/x64 [48 instructions / 6725708491442675303 x1]; 4c2e8d4/PE/x64 [48 instructions / 6725708491442675303 x1].
type:.eq.M8IM12: 4c2e8d4/ELF/x86 [49 instructions / 10339131630906530342 x1]; 4c2e8d4/PE/x86 [50 instructions / 13803000272158448682 x1].
type:.eq.M8IM16: 4c2e8d4/ELF/x64 [42 instructions / 5395798344953128839 x1]; 4c2e8d4/PE/x64 [42 instructions / 5395798344953128839 x1].
type:.eq.M8IM2: 4c2e8d4/ELF/x64 [39 instructions / 15200129864002206882 x1]; 4c2e8d4/ELF/x86 [40 instructions / 12011130991427485237 x1]; 4c2e8d4/PE/x64 [39 instructions / 15200129864002206882 x1]; 4c2e8d4/PE/x86 [41 instructions / 8668096222622985469 x1].
type:.eq.M8IM20K4M8: 4c2e8d4/ELF/x64 [48 instructions / 17369657004121025228 x1]; 4c2e8d4/PE/x64 [48 instructions / 17369657004121025228 x1].
type:.eq.M8IM24: 4c2e8d4/ELF/x64 [44 instructions / 6901234122207303191 x1]; 4c2e8d4/PE/x64 [44 instructions / 6901234122207303191 x1].
type:.eq.M8IM32: 4c2e8d4/ELF/x86 [71 instructions / 2490250727316624816 x1]; 4c2e8d4/PE/x86 [72 instructions / 17393848236210637353 x1].
type:.eq.M8IM8: 4c2e8d4/ELF/x64 [39 instructions / 14971857521365462783 x1]; 4c2e8d4/ELF/x86 [44 instructions / 17887927449800004351 x1]; 4c2e8d4/PE/x64 [39 instructions / 14971857521365462783 x1]; 4c2e8d4/PE/x86 [45 instructions / 14609341128522715272 x1].
type:.eq.M8ISM4K4M16S: 4c2e8d4/ELF/x64 [63 instructions / 6578476133813076608 x1]; 4c2e8d4/PE/x64 [63 instructions / 6578476133813076608 x1].
type:.eq.M8S: 4c2e8d4/ELF/x64 [26 instructions / 10002994300141525680 x1]; 4c2e8d4/ELF/x86 [33 instructions / 12453629563298997243 x1]; 4c2e8d4/PE/x64 [26 instructions / 10002994300141525680 x1]; 4c2e8d4/PE/x86 [34 instructions / 8589410266037254818 x1].
type:.eq.M8SE: 4c2e8d4/ELF/x64 [39 instructions / 2850229506305917583 x1]; 4c2e8d4/ELF/x86 [47 instructions / 9726287644751492227 x1]; 4c2e8d4/PE/x64 [39 instructions / 2850229506305917583 x1]; 4c2e8d4/PE/x86 [48 instructions / 5125560537174465151 x1].
type:.eq.M8SM12: 4c2e8d4/ELF/x64 [32 instructions / 448646495275023991 x1].
type:.eq.M8SM16: 4c2e8d4/PE/x64 [33 instructions / 17168112389029724140 x1].
type:.eq.M8SM1K3M12: 4c2e8d4/ELF/x64 [36 instructions / 8152555327885188872 x1]; 4c2e8d4/PE/x64 [36 instructions / 8152555327885188872 x1].
type:.eq.M8SM2: 4c2e8d4/PE/x64 [29 instructions / 15420435790605690863 x1].
type:.eq.M8SM4: 4c2e8d4/ELF/x64 [30 instructions / 4574909042427205968 x1]; 4c2e8d4/ELF/x86 [36 instructions / 15079878080855114377 x1]; 4c2e8d4/PE/x64 [30 instructions / 4574909042427205968 x1]; 4c2e8d4/PE/x86 [37 instructions / 12236320217177000898 x1].
type:.eq.M8SM48: 4c2e8d4/ELF/x64 [46 instructions / 11539839255322679439 x1]; 4c2e8d4/ELF/x86 [109 instructions / 14195449271360611674 x1]; 4c2e8d4/PE/x64 [46 instructions / 11539839255322679439 x1]; 4c2e8d4/PE/x86 [110 instructions / 17849943286911983714 x1].
type:.eq.M8SM8: 4c2e8d4/PE/x64 [29 instructions / 17962430995236041021 x1]; 4c2e8d4/PE/x86 [47 instructions / 12960637361666599876 x1].
type:.eq.M8SM8I: 4c2e8d4/ELF/x86 [60 instructions / 2087871517809182305 x1]; 4c2e8d4/PE/x86 [61 instructions / 13464731254290433778 x1].
type:.eq.M8SM8SM28K4I: 4c2e8d4/ELF/x64 [65 instructions / 4438460336531777567 x1]; 4c2e8d4/PE/x64 [65 instructions / 4438460336531777567 x1].
type:.eq.M8SS: 4c2e8d4/ELF/x64 [39 instructions / 9488028819342825036 x1]; 4c2e8d4/ELF/x86 [48 instructions / 3220367563652499355 x1]; 4c2e8d4/PE/x64 [39 instructions / 9488028819342825036 x1]; 4c2e8d4/PE/x86 [49 instructions / 14029225895525715355 x1].
type:.eq.M8SSM20: 4c2e8d4/ELF/x86 [77 instructions / 10260011011418456202 x1]; 4c2e8d4/PE/x86 [78 instructions / 14329633860344329906 x1].
type:.eq.M8SSM2K2M8K4M24: 4c2e8d4/PE/x64 [56 instructions / 2260765251857984353 x1].
type:.eq.M8SSM8: 4c2e8d4/ELF/x86 [61 instructions / 16998694443426592661 x1]; 4c2e8d4/PE/x86 [62 instructions / 7589370868321093099 x1].
type:.eq.M8SSS: 4c2e8d4/ELF/x64 [50 instructions / 5269145600201585113 x1]; 4c2e8d4/PE/x64 [50 instructions / 5269145600201585113 x1].
type:.eq.M8SSSS: 4c2e8d4/ELF/x64 [62 instructions / 4190490614027411988 x1]; 4c2e8d4/PE/x64 [62 instructions / 4190490614027411988 x1].
type:.eq.M92K4M28: 4c2e8d4/ELF/x64 [37 instructions / 14571368420932773672 x1]; 4c2e8d4/PE/x64 [37 instructions / 14571368420932773672 x1].
type:.eq.M9K1M10: 4c2e8d4/ELF/x64 [15 instructions / 8829553774247248045 x1]; 4c2e8d4/PE/x64 [15 instructions / 8829553774247248045 x1].
type:.eq.M9K3FFK4M9K7M28: 4c2e8d4/ELF/x64 [38 instructions / 11474410811312946960 x1]; 4c2e8d4/PE/x64 [38 instructions / 11474410811312946960 x1].
type:.eq.M9K3FFM9K3M28: 4c2e8d4/ELF/x86 [76 instructions / 16925311910083985522 x1]; 4c2e8d4/PE/x86 [77 instructions / 13579255046391214519 x1].
type:.eq.M9K3M12: 4c2e8d4/ELF/x86 [36 instructions / 1177378576051391655 x1]; 4c2e8d4/PE/x86 [37 instructions / 12280695452761701751 x1].
type:.eq.M9K3M16: 4c2e8d4/ELF/x64 [15 instructions / 8188376712969998780 x1]; 4c2e8d4/ELF/x86 [40 instructions / 2476771837144895362 x1].
type:.eq.M9K3M16IM4: 4c2e8d4/ELF/x86 [61 instructions / 13179470377600194739 x1]; 4c2e8d4/PE/x86 [62 instructions / 6386420387451308950 x1].
type:.eq.M9K3M17K3I: 4c2e8d4/ELF/x86 [57 instructions / 11721102534075414493 x1]; 4c2e8d4/PE/x86 [58 instructions / 10302518491908434601 x1].
type:.eq.M9K3M20: 4c2e8d4/ELF/x86 [45 instructions / 18404610856232420656 x1]; 4c2e8d4/PE/x86 [46 instructions / 9018960709457823418 x1].
type:.eq.M9K3M4: 4c2e8d4/ELF/x86 [27 instructions / 1187499404062354710 x1]; 4c2e8d4/PE/x86 [28 instructions / 10768225643785054658 x1].
type:.eq.M9K7M16: 4c2e8d4/ELF/x64 [15 instructions / 15039240738670564051 x1]; 4c2e8d4/PE/x64 [15 instructions / 15039240738670564051 x1].
type:.eq.M9K7M16IM4: 4c2e8d4/ELF/x64 [45 instructions / 11720959424298095909 x1]; 4c2e8d4/PE/x64 [45 instructions / 11720959424298095909 x1].
type:.eq.M9K7M17: 4c2e8d4/ELF/x64 [19 instructions / 2945691941987410065 x1]; 4c2e8d4/PE/x64 [19 instructions / 2945691941987410065 x1].
type:.eq.M9K7M20K4M16II: 4c2e8d4/ELF/x64 [60 instructions / 6459720323177594827 x1]; 4c2e8d4/PE/x64 [60 instructions / 6459720323177594827 x1].
type:.eq.M9K7M36K4M8: 4c2e8d4/ELF/x64 [29 instructions / 15003945105056063892 x1]; 4c2e8d4/PE/x64 [29 instructions / 15003945105056063892 x1].
type:.eq.M9K7M8: 4c2e8d4/ELF/x64 [13 instructions / 1342345603704710282 x1]; 4c2e8d4/PE/x64 [13 instructions / 1342345603704710282 x1].
type:.eq.M9K7SM4K4I: 4c2e8d4/ELF/x64 [44 instructions / 4641071952541842057 x1]; 4c2e8d4/PE/x64 [44 instructions / 4641071952541842057 x1].
type:.eq.SE: 4c2e8d4/ELF/x64 [35 instructions / 4070303548277137783 x1]; 4c2e8d4/ELF/x86 [38 instructions / 8648413383237055564 x1].
type:.eq.SI: 4c2e8d4/ELF/x64 [35 instructions / 4070303548277137783 x1]; 4c2e8d4/ELF/x86 [38 instructions / 8648413383237055564 x1]; 4c2e8d4/PE/x64 [35 instructions / 4070303548277137783 x1]; 4c2e8d4/PE/x86 [39 instructions / 925684954760828502 x1].
type:.eq.SII: 4c2e8d4/ELF/x64 [46 instructions / 10079551784146850923 x1]; 4c2e8d4/ELF/x86 [52 instructions / 18130430137444050011 x1]; 4c2e8d4/PE/x64 [46 instructions / 10079551784146850923 x1]; 4c2e8d4/PE/x86 [53 instructions / 7003175552197797088 x1].
type:.eq.SIISIISIISIIM16: 4c2e8d4/ELF/x64 [156 instructions / 4527456625170556727 x1]; 4c2e8d4/PE/x64 [156 instructions / 4527456625170556727 x1].
type:.eq.SIISIISIISIIM8: 4c2e8d4/ELF/x86 [189 instructions / 4460384658864932104 x1]; 4c2e8d4/PE/x86 [190 instructions / 7136104197359792261 x1].
type:.eq.SIM17: 4c2e8d4/ELF/x64 [47 instructions / 2282437778489245298 x1]; 4c2e8d4/PE/x64 [47 instructions / 2282437778489245298 x1].
type:.eq.SIM8IIIIM12: 4c2e8d4/ELF/x86 [119 instructions / 2902940044222314365 x1]; 4c2e8d4/PE/x86 [120 instructions / 9992610078139300923 x1].
type:.eq.SIM8IIIIM24: 4c2e8d4/ELF/x64 [98 instructions / 5976057200177342221 x1]; 4c2e8d4/PE/x64 [98 instructions / 5976057200177342221 x1].
type:.eq.SIM8SSI: 4c2e8d4/ELF/x64 [74 instructions / 17306695942142684836 x1]; 4c2e8d4/ELF/x86 [90 instructions / 14630624175770898697 x1]; 4c2e8d4/PE/x64 [74 instructions / 17306695942142684836 x1]; 4c2e8d4/PE/x86 [91 instructions / 7693076455290429885 x1].
type:.eq.SIM9: 4c2e8d4/ELF/x86 [54 instructions / 7361568293883323455 x1]; 4c2e8d4/PE/x86 [55 instructions / 15745539722691691709 x1].
type:.eq.SM1: 4c2e8d4/ELF/x64 [26 instructions / 12871093078655090180 x1]; 4c2e8d4/ELF/x86 [27 instructions / 8477615008783118757 x1]; 4c2e8d4/PE/x64 [26 instructions / 12871093078655090180 x1]; 4c2e8d4/PE/x86 [28 instructions / 1216716679305340424 x1].
type:.eq.SM10: 4c2e8d4/ELF/x64 [30 instructions / 9089003299929895694 x1]; 4c2e8d4/ELF/x86 [40 instructions / 11028873901343662384 x1]; 4c2e8d4/PE/x64 [30 instructions / 9089003299929895694 x1]; 4c2e8d4/PE/x86 [41 instructions / 18043410658023355229 x1].
type:.eq.SM10K2M16: 4c2e8d4/ELF/x86 [66 instructions / 9010772560851290327 x1]; 4c2e8d4/PE/x86 [67 instructions / 7703354631533475533 x1].
type:.eq.SM10K2M18K2SS: 4c2e8d4/ELF/x86 [99 instructions / 7416609632282968058 x1]; 4c2e8d4/PE/x86 [100 instructions / 17197772176322617157 x1].
type:.eq.SM10K2M1K3SS: 4c2e8d4/ELF/x86 [73 instructions / 13607041622541233069 x1]; 4c2e8d4/PE/x86 [74 instructions / 5359046956828886259 x1].
type:.eq.SM10K2M2K2M8: 4c2e8d4/ELF/x86 [56 instructions / 11294270181196769624 x1]; 4c2e8d4/PE/x86 [57 instructions / 9988668472198089116 x1].
type:.eq.SM10K2M2K2S: 4c2e8d4/ELF/x86 [58 instructions / 96337761876787169 x1]; 4c2e8d4/PE/x86 [59 instructions / 4524553393126950766 x1].
type:.eq.SM10K2M2K2SS: 4c2e8d4/ELF/x86 [73 instructions / 17689711588103305099 x1]; 4c2e8d4/PE/x86 [74 instructions / 11729001694148815117 x1].
type:.eq.SM10K2M3K1S: 4c2e8d4/ELF/x86 [61 instructions / 9594632427531150792 x1]; 4c2e8d4/PE/x86 [62 instructions / 10170164929596022727 x1].
type:.eq.SM10K2M4: 4c2e8d4/ELF/x86 [43 instructions / 14287925384743477947 x1]; 4c2e8d4/PE/x86 [44 instructions / 1898899267889329863 x1].
type:.eq.SM10K2M4S: 4c2e8d4/ELF/x86 [58 instructions / 10714112225291588449 x1]; 4c2e8d4/PE/x86 [59 instructions / 1213125536026811281 x1].
type:.eq.SM10K2M4SSSS: 4c2e8d4/ELF/x86 [103 instructions / 10160357470529940570 x1]; 4c2e8d4/PE/x86 [104 instructions / 9366201021491292865 x1].
type:.eq.SM10K2M5K3S: 4c2e8d4/ELF/x86 [61 instructions / 15998839362680715271 x1]; 4c2e8d4/PE/x86 [62 instructions / 3904721188358479783 x1].
type:.eq.SM10K2M6K2S: 4c2e8d4/ELF/x86 [61 instructions / 5210138929080961744 x1]; 4c2e8d4/PE/x86 [62 instructions / 15926703848531883019 x1].
type:.eq.SM10K2M8: 4c2e8d4/ELF/x86 [51 instructions / 13251027783403126167 x1]; 4c2e8d4/PE/x86 [52 instructions / 11231174345819102379 x1].
type:.eq.SM10K2S: 4c2e8d4/ELF/x86 [55 instructions / 15688727468169611063 x1]; 4c2e8d4/PE/x86 [56 instructions / 18159769901982761633 x1].
type:.eq.SM10K2SM12SM6K2S: 4c2e8d4/ELF/x86 [107 instructions / 1653324424473019790 x1]; 4c2e8d4/PE/x86 [108 instructions / 8985415385651160957 x1].
type:.eq.SM10K2SM14K2SM2K2S: 4c2e8d4/ELF/x86 [114 instructions / 1963220322343743293 x1]; 4c2e8d4/PE/x86 [115 instructions / 11683575841898369186 x1].
type:.eq.SM10K2SS: 4c2e8d4/ELF/x86 [70 instructions / 1525864479177669608 x1]; 4c2e8d4/PE/x86 [71 instructions / 1105256219755339367 x1].
type:.eq.SM10K2SSM20: 4c2e8d4/ELF/x86 [99 instructions / 16796348655657162114 x1]; 4c2e8d4/PE/x86 [100 instructions / 17686958041150631913 x1].
type:.eq.SM10K2SSS: 4c2e8d4/ELF/x86 [85 instructions / 5377163183570723641 x1]; 4c2e8d4/PE/x86 [86 instructions / 13057419015358751691 x1].
type:.eq.SM10K6M16: 4c2e8d4/ELF/x64 [36 instructions / 1105553245323545280 x1]; 4c2e8d4/PE/x64 [36 instructions / 1105553245323545280 x1].
type:.eq.SM10K6M18K6SS: 4c2e8d4/ELF/x64 [67 instructions / 17826583568685143132 x1]; 4c2e8d4/PE/x64 [67 instructions / 17826583568685143132 x1].
type:.eq.SM10K6M1K7SS: 4c2e8d4/ELF/x64 [57 instructions / 5972085886135452249 x1]; 4c2e8d4/PE/x64 [57 instructions / 5972085886135452249 x1].
type:.eq.SM10K6M2K6M8: 4c2e8d4/ELF/x64 [36 instructions / 1302274427568156099 x1]; 4c2e8d4/PE/x64 [36 instructions / 1302274427568156099 x1].
type:.eq.SM10K6M2K6S: 4c2e8d4/ELF/x64 [47 instructions / 11946059951008948794 x1]; 4c2e8d4/PE/x64 [47 instructions / 11946059951008948794 x1].
type:.eq.SM10K6M2K6SS: 4c2e8d4/ELF/x64 [57 instructions / 9304033536434918 x1]; 4c2e8d4/PE/x64 [57 instructions / 9304033536434918 x1].
type:.eq.SM10K6M3K5S: 4c2e8d4/ELF/x64 [50 instructions / 5781047886594879763 x1]; 4c2e8d4/PE/x64 [50 instructions / 5781047886594879763 x1].
type:.eq.SM10K6M4: 4c2e8d4/ELF/x64 [33 instructions / 14358114829284850583 x1]; 4c2e8d4/PE/x64 [33 instructions / 14358114829284850583 x1].
type:.eq.SM10K6M4K4S: 4c2e8d4/ELF/x64 [47 instructions / 16726898705743314700 x1]; 4c2e8d4/PE/x64 [47 instructions / 16726898705743314700 x1].
type:.eq.SM10K6M4K4SSSS: 4c2e8d4/ELF/x64 [83 instructions / 9040320677761376926 x1]; 4c2e8d4/PE/x64 [83 instructions / 9040320677761376926 x1].
type:.eq.SM10K6M5K3S: 4c2e8d4/ELF/x64 [50 instructions / 17068253541655612146 x1]; 4c2e8d4/PE/x64 [50 instructions / 17068253541655612146 x1].
type:.eq.SM10K6M6K2S: 4c2e8d4/ELF/x64 [49 instructions / 15008832348609203286 x1]; 4c2e8d4/PE/x64 [49 instructions / 15008832348609203286 x1].
type:.eq.SM10K6M8: 4c2e8d4/ELF/x64 [32 instructions / 514633343827240527 x1]; 4c2e8d4/PE/x64 [32 instructions / 514633343827240527 x1].
type:.eq.SM10K6S: 4c2e8d4/ELF/x64 [42 instructions / 5467520902397302108 x1]; 4c2e8d4/PE/x64 [42 instructions / 5467520902397302108 x1].
type:.eq.SM10K6SM12K4SM6K2S: 4c2e8d4/ELF/x64 [81 instructions / 9721902801679782230 x1]; 4c2e8d4/PE/x64 [81 instructions / 9721902801679782230 x1].
type:.eq.SM10K6SM14K2SM2K6S: 4c2e8d4/ELF/x64 [79 instructions / 6290538435525452370 x1]; 4c2e8d4/PE/x64 [79 instructions / 6290538435525452370 x1].
type:.eq.SM10K6SS: 4c2e8d4/ELF/x64 [54 instructions / 9233554793182306053 x1]; 4c2e8d4/PE/x64 [54 instructions / 9233554793182306053 x1].
type:.eq.SM10K6SSM20: 4c2e8d4/ELF/x64 [67 instructions / 769842914025216542 x1]; 4c2e8d4/PE/x64 [67 instructions / 769842914025216542 x1].
type:.eq.SM10K6SSS: 4c2e8d4/ELF/x64 [67 instructions / 6547266617814240434 x1]; 4c2e8d4/PE/x64 [67 instructions / 6547266617814240434 x1].
type:.eq.SM11: 4c2e8d4/ELF/x64 [29 instructions / 5499814326611271332 x1]; 4c2e8d4/PE/x64 [29 instructions / 5499814326611271332 x1].
type:.eq.SM110: 4c2e8d4/ELF/x64 [33 instructions / 5755384548095860574 x1]; 4c2e8d4/ELF/x86 [36 instructions / 12632623041070641327 x1]; 4c2e8d4/PE/x64 [33 instructions / 5755384548095860574 x1]; 4c2e8d4/PE/x86 [37 instructions / 9916278281130113137 x1].
type:.eq.SM12: 4c2e8d4/ELF/x86 [40 instructions / 4759291817207414320 x1]; 4c2e8d4/PE/x86 [41 instructions / 18035816461917887509 x1].
type:.eq.SM128: 4c2e8d4/ELF/x86 [36 instructions / 12277381968223220715 x1].
type:.eq.SM12K4M168: 4c2e8d4/ELF/x64 [41 instructions / 18419420134899882321 x1].
type:.eq.SM12K4M8: 4c2e8d4/ELF/x64 [33 instructions / 14339388030107954886 x1]; 4c2e8d4/PE/x64 [33 instructions / 14339388030107954886 x1].
type:.eq.SM13K3M13: 4c2e8d4/ELF/x86 [76 instructions / 14950747208776860939 x1]; 4c2e8d4/PE/x86 [77 instructions / 16972484090495246071 x1].
type:.eq.SM16: 4c2e8d4/ELF/x64 [30 instructions / 109523908959432917 x1]; 4c2e8d4/ELF/x86 [50 instructions / 9008168282744567219 x1]; 4c2e8d4/PE/x64 [30 instructions / 109523908959432917 x1]; 4c2e8d4/PE/x86 [51 instructions / 5333184794456142461 x1].
type:.eq.SM16S: 4c2e8d4/ELF/x86 [65 instructions / 647866691091117684 x1]; 4c2e8d4/PE/x86 [66 instructions / 5025758152858006837 x1].
type:.eq.SM17: 4c2e8d4/PE/x64 [33 instructions / 3186514330572205846 x1].
type:.eq.SM17K3M12: 4c2e8d4/ELF/x64 [39 instructions / 16080080856644118090 x1]; 4c2e8d4/PE/x64 [39 instructions / 16080080856644118090 x1].
type:.eq.SM18K2M4: 4c2e8d4/ELF/x86 [56 instructions / 7806525300740645333 x1]; 4c2e8d4/PE/x86 [57 instructions / 1151998010866059213 x1].
type:.eq.SM1K3IIM4: 4c2e8d4/ELF/x86 [62 instructions / 750757871644018581 x1]; 4c2e8d4/PE/x86 [63 instructions / 991143783300430839 x1].
type:.eq.SM1K3M12: 4c2e8d4/PE/x86 [44 instructions / 1314311825446529352 x1].
type:.eq.SM1K3M8K4M8: 4c2e8d4/PE/x64 [33 instructions / 14060746148817451587 x1].
type:.eq.SM1K3SS: 4c2e8d4/ELF/x86 [57 instructions / 13846952824741617869 x1]; 4c2e8d4/PE/x86 [58 instructions / 12142488544940189757 x1].
type:.eq.SM1K7IIM8: 4c2e8d4/ELF/x64 [57 instructions / 9349728326214867540 x1]; 4c2e8d4/PE/x64 [57 instructions / 9349728326214867540 x1].
type:.eq.SM1K7SS: 4c2e8d4/ELF/x64 [49 instructions / 9850918052848390654 x1]; 4c2e8d4/PE/x64 [49 instructions / 9850918052848390654 x1].
type:.eq.SM2: 4c2e8d4/ELF/x64 [26 instructions / 17991486262860467438 x1]; 4c2e8d4/ELF/x86 [27 instructions / 5749399175084895421 x1]; 4c2e8d4/PE/x64 [26 instructions / 17991486262860467438 x1]; 4c2e8d4/PE/x86 [28 instructions / 1295147957495349577 x1].
type:.eq.SM20K4M12: 4c2e8d4/ELF/x64 [39 instructions / 15561296466076322715 x1]; 4c2e8d4/PE/x64 [39 instructions / 15561296466076322715 x1].
type:.eq.SM24: 4c2e8d4/PE/x64 [32 instructions / 5612672303622631001 x1].
type:.eq.SM24S: 4c2e8d4/ELF/x64 [47 instructions / 15319077106882625100 x1]; 4c2e8d4/PE/x64 [47 instructions / 15319077106882625100 x1].
type:.eq.SM25K7M25: 4c2e8d4/ELF/x64 [50 instructions / 2947779502350302713 x1]; 4c2e8d4/PE/x64 [50 instructions / 2947779502350302713 x1].
type:.eq.SM26K6M8: 4c2e8d4/ELF/x64 [40 instructions / 3295320060291051489 x1]; 4c2e8d4/PE/x64 [40 instructions / 3295320060291051489 x1].
type:.eq.SM28: 4c2e8d4/ELF/x86 [66 instructions / 13706732614763772063 x1]; 4c2e8d4/PE/x86 [67 instructions / 765841715544994753 x1].
type:.eq.SM2K2M8: 4c2e8d4/PE/x64 [30 instructions / 10436345346937089996 x1]; 4c2e8d4/PE/x86 [41 instructions / 12609233352702628088 x1].
type:.eq.SM3: 4c2e8d4/ELF/x64 [29 instructions / 3687543011042438351 x1]; 4c2e8d4/ELF/x86 [30 instructions / 1182361143525204854 x1]; 4c2e8d4/PE/x64 [29 instructions / 3687543011042438351 x1]; 4c2e8d4/PE/x86 [31 instructions / 866341355196429171 x1].
type:.eq.SM31K1SSSSM1: 4c2e8d4/ELF/x86 [139 instructions / 706723456649174530 x1]; 4c2e8d4/PE/x86 [140 instructions / 8035352371804264122 x1].
type:.eq.SM32: 4c2e8d4/ELF/x64 [36 instructions / 10868042851365484103 x1]; 4c2e8d4/ELF/x86 [76 instructions / 13809639664837135568 x1]; 4c2e8d4/PE/x64 [36 instructions / 10868042851365484103 x1]; 4c2e8d4/PE/x86 [77 instructions / 14619627121204973773 x1].
type:.eq.SM35K5SSSSM1: 4c2e8d4/ELF/x64 [98 instructions / 8012233132726521594 x1]; 4c2e8d4/PE/x64 [98 instructions / 8012233132726521594 x1].
type:.eq.SM3K1M2K2M20SS: 4c2e8d4/ELF/x86 [92 instructions / 12630062006049631226 x1]; 4c2e8d4/PE/x86 [93 instructions / 7842347848421608383 x1].
type:.eq.SM3K1M2K2M24SS: 4c2e8d4/ELF/x64 [68 instructions / 6085791536364063253 x1]; 4c2e8d4/PE/x64 [68 instructions / 6085791536364063253 x1].
type:.eq.SM4: 4c2e8d4/ELF/x64 [26 instructions / 11111348742126156123 x1]; 4c2e8d4/ELF/x86 [27 instructions / 9337091116904489899 x1]; 4c2e8d4/PE/x64 [26 instructions / 11111348742126156123 x1]; 4c2e8d4/PE/x86 [28 instructions / 5932278877165014730 x1].
type:.eq.SM40: 4c2e8d4/ELF/x64 [40 instructions / 13987986893470368045 x1]; 4c2e8d4/ELF/x86 [87 instructions / 6461175996119336533 x1]; 4c2e8d4/PE/x64 [40 instructions / 13987986893470368045 x1]; 4c2e8d4/PE/x86 [88 instructions / 13414324547333912366 x1].
type:.eq.SM4IM25K3M4: 4c2e8d4/ELF/x86 [78 instructions / 6622977218569663395 x1]; 4c2e8d4/PE/x86 [79 instructions / 2784298445907562347 x1].
type:.eq.SM4IM4: 4c2e8d4/ELF/x86 [48 instructions / 9273142946326259702 x1]; 4c2e8d4/PE/x86 [49 instructions / 13238128834911519184 x1].
type:.eq.SM4IM8: 4c2e8d4/ELF/x86 [52 instructions / 5703884509263593658 x1]; 4c2e8d4/PE/x86 [53 instructions / 6726637563867123166 x1].
type:.eq.SM4IM8IM3K1M20: 4c2e8d4/ELF/x86 [95 instructions / 521922742529915482 x1]; 4c2e8d4/PE/x86 [96 instructions / 7176077587706612290 x1].
type:.eq.SM4K4M16: 4c2e8d4/ELF/x64 [33 instructions / 16693150138256220313 x1]; 4c2e8d4/PE/x64 [33 instructions / 16693150138256220313 x1].
type:.eq.SM4K4M8: 4c2e8d4/ELF/x64 [29 instructions / 1769650823460365915 x1]; 4c2e8d4/PE/x64 [29 instructions / 1769650823460365915 x1].
type:.eq.SM4K4S: 4c2e8d4/ELF/x64 [41 instructions / 5234792593217712434 x1]; 4c2e8d4/PE/x64 [41 instructions / 5234792593217712434 x1].
type:.eq.SM4S: 4c2e8d4/ELF/x86 [42 instructions / 3211744507798148404 x1]; 4c2e8d4/PE/x86 [43 instructions / 1500203130937162526 x1].
type:.eq.SM4SM4: 4c2e8d4/ELF/x86 [45 instructions / 689194653104361261 x1]; 4c2e8d4/PE/x86 [46 instructions / 2580817045851070467 x1].
type:.eq.SM5: 4c2e8d4/ELF/x86 [30 instructions / 16935174188902864502 x1]; 4c2e8d4/PE/x86 [31 instructions / 5114380470743370962 x1].
type:.eq.SM52K4SM13: 4c2e8d4/PE/x64 [69 instructions / 5723366796425183402 x1].
type:.eq.SM52SM13: 4c2e8d4/PE/x86 [147 instructions / 18129089601105947202 x1].
type:.eq.SM56: 4c2e8d4/ELF/x64 [46 instructions / 3363882892856008436 x1]; 4c2e8d4/PE/x64 [46 instructions / 3363882892856008436 x1].
type:.eq.SM5K3I: 4c2e8d4/ELF/x64 [43 instructions / 2214637228610012437 x1]; 4c2e8d4/ELF/x86 [44 instructions / 18113078605801630178 x1]; 4c2e8d4/PE/x64 [43 instructions / 2214637228610012437 x1]; 4c2e8d4/PE/x86 [45 instructions / 14922558438007692834 x1].
type:.eq.SM6: 4c2e8d4/ELF/x64 [29 instructions / 6122230273363098358 x1]; 4c2e8d4/ELF/x86 [30 instructions / 5159481105455977060 x1]; 4c2e8d4/PE/x64 [29 instructions / 6122230273363098358 x1]; 4c2e8d4/PE/x86 [31 instructions / 9622743951269348406 x1].
type:.eq.SM64: 4c2e8d4/ELF/x64 [50 instructions / 13264379958131788658 x1]; 4c2e8d4/ELF/x86 [124 instructions / 14614078044226232789 x1]; 4c2e8d4/PE/x64 [50 instructions / 13264379958131788658 x1]; 4c2e8d4/PE/x86 [125 instructions / 14739989636495183531 x1].
type:.eq.SM64IM16: 4c2e8d4/ELF/x86 [162 instructions / 13400504317404376372 x1]; 4c2e8d4/PE/x86 [163 instructions / 15681229153266494479 x1].
type:.eq.SM64IM24: 4c2e8d4/ELF/x64 [76 instructions / 6108539791598294749 x1]; 4c2e8d4/PE/x64 [76 instructions / 6108539791598294749 x1].
type:.eq.SM6K2SM6: 4c2e8d4/ELF/x86 [51 instructions / 3520995543867087216 x1]; 4c2e8d4/PE/x86 [52 instructions / 13349981315256704091 x1].
type:.eq.SM7: 4c2e8d4/ELF/x86 [30 instructions / 1038568794667038205 x1]; 4c2e8d4/PE/x86 [31 instructions / 4858969620310950161 x1].
type:.eq.SM7K1SM7: 4c2e8d4/ELF/x86 [51 instructions / 17909776112015885791 x1]; 4c2e8d4/PE/x86 [52 instructions / 7101193600419203848 x1].
type:.eq.SM8: 4c2e8d4/ELF/x64 [26 instructions / 15276697144342868976 x1]; 4c2e8d4/ELF/x86 [37 instructions / 4416601710694342252 x1]; 4c2e8d4/PE/x64 [26 instructions / 15276697144342868976 x1]; 4c2e8d4/PE/x86 [38 instructions / 3883020532757658232 x1].
type:.eq.SM8IM12K4IM3K5M32: 4c2e8d4/ELF/x64 [82 instructions / 11892161578789910696 x1]; 4c2e8d4/PE/x64 [82 instructions / 11892161578789910696 x1].
type:.eq.SM8IM16: 4c2e8d4/ELF/x64 [49 instructions / 17529169113180627680 x1]; 4c2e8d4/PE/x64 [49 instructions / 17529169113180627680 x1].
type:.eq.SM8IM37K3M8: 4c2e8d4/ELF/x64 [63 instructions / 10481626057511270230 x1]; 4c2e8d4/PE/x64 [63 instructions / 10481626057511270230 x1].
type:.eq.SM8IM4: 4c2e8d4/ELF/x86 [58 instructions / 4429256824008212354 x1]; 4c2e8d4/PE/x86 [59 instructions / 17817591287377902630 x1].
type:.eq.SM8IM8: 4c2e8d4/ELF/x64 [46 instructions / 10806884631136407234 x1]; 4c2e8d4/PE/x64 [46 instructions / 10806884631136407234 x1].
type:.eq.SM9: 4c2e8d4/ELF/x64 [29 instructions / 490189708062996527 x1]; 4c2e8d4/ELF/x86 [40 instructions / 1252758724273701368 x1]; 4c2e8d4/PE/x64 [29 instructions / 490189708062996527 x1]; 4c2e8d4/PE/x86 [41 instructions / 13934849402622725560 x1].
type:.eq.SM9K3M8: 4c2e8d4/ELF/x86 [51 instructions / 1524702820435675430 x1]; 4c2e8d4/PE/x86 [52 instructions / 16059053174417974931 x1].
type:.eq.SS: 4c2e8d4/ELF/x64 [36 instructions / 5880093290664381757 x1]; 4c2e8d4/ELF/x86 [39 instructions / 9506222921792340663 x1]; 4c2e8d4/PE/x64 [36 instructions / 5880093290664381757 x1]; 4c2e8d4/PE/x86 [40 instructions / 4071608573326130388 x1].
type:.eq.SSI: 4c2e8d4/ELF/x64 [46 instructions / 1929195514915276687 x1]; 4c2e8d4/ELF/x86 [53 instructions / 8056741844055696678 x1]; 4c2e8d4/PE/x64 [46 instructions / 1929195514915276687 x1]; 4c2e8d4/PE/x86 [54 instructions / 3824457671252672428 x1].
type:.eq.SSIII: 4c2e8d4/ELF/x64 [68 instructions / 8276663757741661867 x1]; 4c2e8d4/ELF/x86 [81 instructions / 13455846572162872827 x1]; 4c2e8d4/PE/x64 [68 instructions / 8276663757741661867 x1]; 4c2e8d4/PE/x86 [82 instructions / 13888441452499102994 x1].
type:.eq.SSIM16: 4c2e8d4/ELF/x86 [73 instructions / 12666236569761861319 x1]; 4c2e8d4/PE/x86 [74 instructions / 12206782838148896529 x1].
type:.eq.SSIM32: 4c2e8d4/ELF/x64 [65 instructions / 17418532755950342099 x1]; 4c2e8d4/PE/x64 [65 instructions / 17418532755950342099 x1].
type:.eq.SSIS: 4c2e8d4/ELF/x64 [59 instructions / 2838988321642264899 x1]; 4c2e8d4/ELF/x86 [67 instructions / 7570262327974442485 x1].
type:.eq.SSISM12: 4c2e8d4/ELF/x86 [83 instructions / 1434991150884314687 x1]; 4c2e8d4/PE/x86 [84 instructions / 6115686838080096130 x1].
type:.eq.SSISM4K4M16: 4c2e8d4/ELF/x64 [67 instructions / 14642946442864945612 x1]; 4c2e8d4/PE/x64 [67 instructions / 14642946442864945612 x1].
type:.eq.SSM1: 4c2e8d4/ELF/x64 [41 instructions / 4562459933114830922 x1]; 4c2e8d4/ELF/x86 [42 instructions / 10119286473052660527 x1]; 4c2e8d4/PE/x64 [41 instructions / 4562459933114830922 x1]; 4c2e8d4/PE/x86 [43 instructions / 8440756201913619846 x1].
type:.eq.SSM12: 4c2e8d4/ELF/x86 [55 instructions / 5461209507082831740 x1]; 4c2e8d4/PE/x86 [56 instructions / 821937201710413136 x1].
type:.eq.SSM16: 4c2e8d4/ELF/x64 [42 instructions / 3068058388882147010 x1]; 4c2e8d4/PE/x64 [42 instructions / 3068058388882147010 x1].
type:.eq.SSM1K3M4: 4c2e8d4/PE/x86 [46 instructions / 6815645069008271687 x1].
type:.eq.SSM1K7M8: 4c2e8d4/ELF/x64 [42 instructions / 4461205807389208225 x1]; 4c2e8d4/PE/x64 [42 instructions / 4461205807389208225 x1].
type:.eq.SSM2K2M4S: 4c2e8d4/ELF/x86 [60 instructions / 1385919938201371805 x1]; 4c2e8d4/PE/x86 [61 instructions / 572435413998319127 x1].
type:.eq.SSM2K6M8S: 4c2e8d4/ELF/x64 [54 instructions / 9448412817732702368 x1]; 4c2e8d4/PE/x64 [54 instructions / 9448412817732702368 x1].
type:.eq.SSM32: 4c2e8d4/ELF/x64 [49 instructions / 15607872647447677952 x1]; 4c2e8d4/ELF/x86 [91 instructions / 18193636506116445027 x1].
type:.eq.SSM36: 4c2e8d4/ELF/x64 [51 instructions / 10926520804937954300 x1]; 4c2e8d4/ELF/x86 [94 instructions / 7113259081937523155 x1]; 4c2e8d4/PE/x64 [51 instructions / 10926520804937954300 x1]; 4c2e8d4/PE/x86 [95 instructions / 4652947563476845256 x1].
type:.eq.SSM4: 4c2e8d4/ELF/x86 [42 instructions / 13727096769921024810 x1]; 4c2e8d4/PE/x64 [41 instructions / 11830297083253213493 x1]; 4c2e8d4/PE/x86 [43 instructions / 797164473120415366 x1].
type:.eq.SSM4I: 4c2e8d4/ELF/x86 [56 instructions / 11222726459300992242 x1].
type:.eq.SSM4K4I: 4c2e8d4/ELF/x64 [51 instructions / 17737276160716393593 x1].
type:.eq.SSM4SM2: 4c2e8d4/ELF/x86 [60 instructions / 1748060013007505949 x1]; 4c2e8d4/PE/x86 [61 instructions / 15613331222686874127 x1].
type:.eq.SSM4SSSSSSM2: 4c2e8d4/ELF/x86 [135 instructions / 4779931672666306449 x1]; 4c2e8d4/PE/x86 [136 instructions / 2361613533450218880 x1].
type:.eq.SSM7K1S: 4c2e8d4/ELF/x64 [54 instructions / 15297632495286918173 x1]; 4c2e8d4/ELF/x86 [60 instructions / 5294216952393858693 x1]; 4c2e8d4/PE/x64 [54 instructions / 15297632495286918173 x1]; 4c2e8d4/PE/x86 [61 instructions / 13929317604231361342 x1].
type:.eq.SSM8: 4c2e8d4/ELF/x64 [40 instructions / 9440659264004007131 x1]; 4c2e8d4/PE/x64 [40 instructions / 9440659264004007131 x1].
type:.eq.SSM8SM2: 4c2e8d4/ELF/x64 [54 instructions / 5416517249735678457 x1]; 4c2e8d4/PE/x64 [54 instructions / 5416517249735678457 x1].
type:.eq.SSM8SSSSSSM2: 4c2e8d4/ELF/x64 [116 instructions / 14156288293573746883 x1]; 4c2e8d4/PE/x64 [116 instructions / 14156288293573746883 x1].
type:.eq.SSS: 4c2e8d4/ELF/x64 [48 instructions / 5035907808307167663 x1]; 4c2e8d4/ELF/x86 [54 instructions / 15633799646637126007 x1]; 4c2e8d4/PE/x64 [48 instructions / 5035907808307167663 x1]; 4c2e8d4/PE/x86 [55 instructions / 5658872124063039344 x1].
type:.eq.SSSI: 4c2e8d4/ELF/x64 [60 instructions / 6784590532207777857 x1]; 4c2e8d4/ELF/x86 [68 instructions / 841154676178033610 x1]; 4c2e8d4/PE/x64 [60 instructions / 6784590532207777857 x1]; 4c2e8d4/PE/x86 [69 instructions / 13188558464317652307 x1].
type:.eq.SSSM1: 4c2e8d4/ELF/x64 [49 instructions / 6863927380808399541 x1]; 4c2e8d4/ELF/x86 [57 instructions / 14456168717670915431 x1]; 4c2e8d4/PE/x64 [49 instructions / 6863927380808399541 x1]; 4c2e8d4/PE/x86 [58 instructions / 4653254085228649739 x1].
type:.eq.SSSM1K3S: 4c2e8d4/ELF/x86 [72 instructions / 16771754479335500287 x1]; 4c2e8d4/PE/x86 [73 instructions / 7135908184326747376 x1].
type:.eq.SSSM1K7S: 4c2e8d4/ELF/x64 [65 instructions / 5834018295151798181 x1]; 4c2e8d4/PE/x64 [65 instructions / 5834018295151798181 x1].
type:.eq.SSSM4: 4c2e8d4/ELF/x86 [57 instructions / 6493082879223600557 x1]; 4c2e8d4/PE/x86 [58 instructions / 13710388135416679858 x1].
type:.eq.SSSM8: 4c2e8d4/ELF/x64 [49 instructions / 3374054629434158925 x1]; 4c2e8d4/PE/x64 [49 instructions / 3374054629434158925 x1].
type:.eq.SSSS: 4c2e8d4/ELF/x86 [69 instructions / 16766398326046980702 x1]; 4c2e8d4/PE/x86 [70 instructions / 8958287793903245486 x1].
type:.eq.SSSSS: 4c2e8d4/ELF/x86 [84 instructions / 3713335585245844365 x1]; 4c2e8d4/PE/x86 [85 instructions / 7982682699501454074 x1].
type:.eq.SSSSSS: 4c2e8d4/ELF/x86 [99 instructions / 18201963233109636151 x1]; 4c2e8d4/PE/x86 [100 instructions / 15511375285909591658 x1].
type:.eq.SSSSSSS: 4c2e8d4/ELF/x86 [114 instructions / 9687202908296203672 x1]; 4c2e8d4/PE/x86 [115 instructions / 17161611276729974095 x1].
type:.eq.SSSSSSSS: 4c2e8d4/ELF/x64 [106 instructions / 18083294807921802227 x1]; 4c2e8d4/ELF/x86 [129 instructions / 11894289615705612234 x1]; 4c2e8d4/PE/x64 [106 instructions / 18083294807921802227 x1]; 4c2e8d4/PE/x86 [130 instructions / 13638656806661116089 x1].
type:.eq.SSS[2SSSS]: 4c2e8d4/ELF/x86 [75 instructions / 5854175213479620734 x1]; 4c2e8d4/PE/x86 [76 instructions / 3846796629945487318 x1].
type:.eq.SSS[3SSSS]: 4c2e8d4/ELF/x86 [75 instructions / 4535495946575353138 x1]; 4c2e8d4/PE/x86 [76 instructions / 13219574837619514681 x1].
type:.eq.SSS[4SSSS]: 4c2e8d4/ELF/x86 [75 instructions / 4726836879518765313 x1]; 4c2e8d4/PE/x86 [76 instructions / 1586833508155731702 x1].
type:.eq.SSS[5SSSS]: 4c2e8d4/ELF/x86 [75 instructions / 3971309599689010371 x1]; 4c2e8d4/PE/x86 [76 instructions / 15968335427074655631 x1].
type:.eq.SS[2SSSS]: 4c2e8d4/ELF/x86 [60 instructions / 12902686528071928055 x1]; 4c2e8d4/PE/x86 [61 instructions / 17038382548451590637 x1].
type:.eq.SS[3SSSS]: 4c2e8d4/ELF/x86 [60 instructions / 11717231367671977918 x1]; 4c2e8d4/PE/x86 [61 instructions / 1105972210438919550 x1].
type:.eq.SS[4SSSS]: 4c2e8d4/ELF/x86 [60 instructions / 17078303766810828376 x1]; 4c2e8d4/PE/x86 [61 instructions / 3266899392020642838 x1].
type:.eq.SS[5SSSS]: 4c2e8d4/ELF/x86 [60 instructions / 8743810528079563908 x1]; 4c2e8d4/PE/x86 [61 instructions / 17133909111107717973 x1].
type:.eq.S[11SS]: 4c2e8d4/ELF/x64 [44 instructions / 13758931533618772402 x1]; 4c2e8d4/PE/x64 [44 instructions / 13758931533618772402 x1].
type:.eq.S[14SSSS]: 4c2e8d4/ELF/x86 [45 instructions / 3689315427842859078 x1]; 4c2e8d4/PE/x86 [46 instructions / 10962688812104749535 x1].
type:.eq.S[14SS]: 4c2e8d4/ELF/x64 [44 instructions / 4976232610347589349 x1]; 4c2e8d4/PE/x64 [44 instructions / 4976232610347589349 x1].
type:.eq.S[28SS]: 4c2e8d4/ELF/x64 [44 instructions / 12421481526137041647 x1]; 4c2e8d4/PE/x64 [44 instructions / 12421481526137041647 x1].
type:.eq.S[2SSSS]: 4c2e8d4/ELF/x86 [45 instructions / 14465712483347293995 x1]; 4c2e8d4/PE/x86 [46 instructions / 10456189281367165757 x1].
type:.eq.S[2SS]: 4c2e8d4/ELF/x64 [44 instructions / 7066105982971657418 x1]; 4c2e8d4/PE/x64 [44 instructions / 7066105982971657418 x1].
type:.eq.S[3SSSS]: 4c2e8d4/ELF/x86 [45 instructions / 9624153818759815392 x1]; 4c2e8d4/PE/x86 [46 instructions / 11948314356749696902 x1].
type:.eq.S[3SS]: 4c2e8d4/ELF/x64 [44 instructions / 16180013182224092467 x1]; 4c2e8d4/PE/x64 [44 instructions / 16180013182224092467 x1].
type:.eq.S[4SSSS]: 4c2e8d4/ELF/x86 [45 instructions / 11347898535160344409 x1]; 4c2e8d4/PE/x86 [46 instructions / 18171157132635540254 x1].
type:.eq.S[4SS]: 4c2e8d4/ELF/x64 [44 instructions / 462061105004569786 x1]; 4c2e8d4/PE/x64 [44 instructions / 462061105004569786 x1].
type:.eq.S[5SS]: 4c2e8d4/ELF/x64 [44 instructions / 3811490420080142542 x1]; 4c2e8d4/PE/x64 [44 instructions / 3811490420080142542 x1].
type:.eq.S[6SS]: 4c2e8d4/ELF/x64 [44 instructions / 6857197187598391535 x1]; 4c2e8d4/PE/x64 [44 instructions / 6857197187598391535 x1].
type:.eq.S[7SSSS]: 4c2e8d4/ELF/x86 [45 instructions / 16407456495728322950 x1]; 4c2e8d4/PE/x86 [46 instructions / 9525552937254963509 x1].
type:.eq.S[7SS]: 4c2e8d4/ELF/x64 [44 instructions / 4311876107701958973 x1]; 4c2e8d4/PE/x64 [44 instructions / 4311876107701958973 x1].
type:.eq.S[8SS]: 4c2e8d4/ELF/x64 [44 instructions / 11456907382053082938 x1]; 4c2e8d4/PE/x64 [44 instructions / 11456907382053082938 x1].
type:.eq.S[9SS]: 4c2e8d4/ELF/x64 [44 instructions / 2880003838652773668 x1]; 4c2e8d4/PE/x64 [44 instructions / 2880003838652773668 x1].
type:.eq.[10SS]: 4c2e8d4/ELF/x64 [35 instructions / 6084902725440314225 x1]; 4c2e8d4/PE/x64 [35 instructions / 6084902725440314225 x1].
type:.eq.[11SS]: 4c2e8d4/ELF/x64 [35 instructions / 501925229237226961 x1]; 4c2e8d4/PE/x64 [35 instructions / 501925229237226961 x1].
type:.eq.[128IM32]: 4c2e8d4/ELF/x64 [35 instructions / 8532276595394367668 x1]; 4c2e8d4/PE/x64 [35 instructions / 8532276595394367668 x1].
type:.eq.[128M12K4M57K7M44K4M10K6]: 4c2e8d4/ELF/x64 [35 instructions / 11099884566574888850 x1]; 4c2e8d4/PE/x64 [35 instructions / 11099884566574888850 x1].
type:.eq.[128M17K7M9K7M27K5]: 4c2e8d4/ELF/x64 [35 instructions / 5034581441612260133 x1]; 4c2e8d4/PE/x64 [35 instructions / 5034581441612260133 x1].
type:.eq.[128M9K7M36K4M8]: 4c2e8d4/ELF/x64 [35 instructions / 17265881739258995096 x1]; 4c2e8d4/PE/x64 [35 instructions / 17265881739258995096 x1].
type:.eq.[128SS]: 4c2e8d4/ELF/x64 [35 instructions / 15546884980840414359 x1]; 4c2e8d4/PE/x64 [35 instructions / 15546884980840414359 x1].
type:.eq.[128[4II]M8]: 4c2e8d4/ELF/x64 [35 instructions / 14637161997361262485 x1]; 4c2e8d4/PE/x64 [35 instructions / 14637161997361262485 x1].
type:.eq.[128[8M20K4]M8]: 4c2e8d4/ELF/x64 [35 instructions / 12883621746986536619 x1]; 4c2e8d4/PE/x64 [35 instructions / 12883621746986536619 x1].
type:.eq.[16SS]: 4c2e8d4/ELF/x64 [35 instructions / 617025508462967916 x1]; 4c2e8d4/PE/x64 [35 instructions / 617025508462967916 x1].
type:.eq.[20SM4SM4]: 4c2e8d4/ELF/x86 [30 instructions / 5702926095865458607 x1]; 4c2e8d4/PE/x86 [31 instructions / 17778065429436604469 x1].
type:.eq.[25SM7K1SM7K1]: 4c2e8d4/ELF/x86 [30 instructions / 12696111935157354078 x1]; 4c2e8d4/PE/x86 [31 instructions / 3499150393126601761 x1].
type:.eq.[2EE]: 4c2e8d4/ELF/x64 [35 instructions / 17666174901710332653 x1]; 4c2e8d4/PE/x64 [35 instructions / 17666174901710332653 x1].
type:.eq.[2M16SSM40]: 4c2e8d4/ELF/x64 [35 instructions / 2570484773759854202 x1]; 4c2e8d4/PE/x64 [35 instructions / 2570484773759854202 x1].
type:.eq.[2M32]: 4c2e8d4/ELF/x86 [30 instructions / 9962324500489839660 x1]; 4c2e8d4/PE/x86 [31 instructions / 5244293256926175242 x1].
type:.eq.[2M8SM4K4]: 4c2e8d4/ELF/x64 [35 instructions / 17666174901710332653 x1]; 4c2e8d4/PE/x64 [35 instructions / 17666174901710332653 x1].
type:.eq.[2M8SM4]: 4c2e8d4/ELF/x86 [30 instructions / 4107410410555007561 x1]; 4c2e8d4/PE/x86 [31 instructions / 8959282189225353711 x1].
type:.eq.[2M8SSM20]: 4c2e8d4/ELF/x86 [30 instructions / 7711725652832203450 x1]; 4c2e8d4/PE/x86 [31 instructions / 2512798017385567713 x1].
type:.eq.[2SSSS]: 4c2e8d4/ELF/x86 [30 instructions / 9962324500489839660 x1]; 4c2e8d4/PE/x86 [31 instructions / 5244293256926175242 x1].
type:.eq.[2SS]: 4c2e8d4/ELF/x64 [35 instructions / 17666174901710332653 x1]; 4c2e8d4/PE/x64 [35 instructions / 17666174901710332653 x1].
type:.eq.[3SSSS]: 4c2e8d4/ELF/x86 [30 instructions / 6282172593291036037 x1]; 4c2e8d4/PE/x86 [31 instructions / 514037354565550989 x1].
type:.eq.[3SS]: 4c2e8d4/ELF/x64 [35 instructions / 6431584550979460940 x1]; 4c2e8d4/PE/x64 [35 instructions / 6431584550979460940 x1].
type:.eq.[40SM8]: 4c2e8d4/ELF/x64 [35 instructions / 4534420714956891279 x1]; 4c2e8d4/PE/x64 [35 instructions / 4534420714956891279 x1].
type:.eq.[45SM11K5]: 4c2e8d4/ELF/x64 [35 instructions / 6898506166613903270 x1]; 4c2e8d4/PE/x64 [35 instructions / 6898506166613903270 x1].
type:.eq.[4II]: 4c2e8d4/ELF/x64 [35 instructions / 1778173491256027864 x1]; 4c2e8d4/PE/x64 [35 instructions / 1778173491256027864 x1].
type:.eq.[4II]M8: 4c2e8d4/ELF/x64 [37 instructions / 6893552651469294757 x1]; 4c2e8d4/PE/x64 [37 instructions / 6893552651469294757 x1].
type:.eq.[4M32]: 4c2e8d4/ELF/x64 [35 instructions / 1778173491256027864 x1]; 4c2e8d4/PE/x64 [35 instructions / 1778173491256027864 x1].
type:.eq.[4SM6K2SM6K2]: 4c2e8d4/ELF/x86 [30 instructions / 13365229123133730400 x1]; 4c2e8d4/PE/x86 [31 instructions / 11428841445707793198 x1].
type:.eq.[4SS]: 4c2e8d4/ELF/x64 [35 instructions / 1778173491256027864 x1]; 4c2e8d4/PE/x64 [35 instructions / 1778173491256027864 x1].
type:.eq.[50SM11K5]: 4c2e8d4/ELF/x64 [35 instructions / 13010421804643662483 x1]; 4c2e8d4/PE/x64 [35 instructions / 13010421804643662483 x1].
type:.eq.[5SSSS]: 4c2e8d4/ELF/x86 [30 instructions / 5440704284917810153 x1]; 4c2e8d4/PE/x86 [31 instructions / 11048912073263264100 x1].
type:.eq.[5SS]: 4c2e8d4/ELF/x64 [35 instructions / 2459802714134665318 x1]; 4c2e8d4/PE/x64 [35 instructions / 2459802714134665318 x1].
type:.eq.[64SSSS]: 4c2e8d4/ELF/x86 [30 instructions / 18344230165263665647 x1]; 4c2e8d4/PE/x86 [31 instructions / 1364350973671578170 x1].
type:.eq.[6SS]: 4c2e8d4/ELF/x64 [35 instructions / 6516834891405778190 x1]; 4c2e8d4/PE/x64 [35 instructions / 6516834891405778190 x1].
type:.eq.[7SS]: 4c2e8d4/ELF/x64 [35 instructions / 2784699325626279339 x1]; 4c2e8d4/PE/x64 [35 instructions / 2784699325626279339 x1].
type:.eq.[8M20K4]: 4c2e8d4/ELF/x64 [35 instructions / 9434603911940660167 x1]; 4c2e8d4/PE/x64 [35 instructions / 9434603911940660167 x1].
type:.eq.[8M20K4]M8: 4c2e8d4/ELF/x64 [37 instructions / 6458983536553199808 x1]; 4c2e8d4/PE/x64 [37 instructions / 6458983536553199808 x1].
type:.eq.[8SM10K6]: 4c2e8d4/ELF/x64 [35 instructions / 10948102357238525546 x1]; 4c2e8d4/PE/x64 [35 instructions / 10948102357238525546 x1].
type:.eq.[8SSSS]: 4c2e8d4/ELF/x86 [30 instructions / 5871794305229490692 x1]; 4c2e8d4/PE/x86 [31 instructions / 13998455913049176903 x1].
type:.eq.[9SS]: 4c2e8d4/ELF/x64 [35 instructions / 7014511427836773485 x1]; 4c2e8d4/PE/x64 [35 instructions / 7014511427836773485 x1].
type:.hash.M16I: 4c2e8d4/ELF/x64 [22 instructions / 13266858301306108134 x1]; 4c2e8d4/PE/x64 [22 instructions / 13266858301306108134 x1].
type:.hash.M16S: 4c2e8d4/ELF/x64 [22 instructions / 13266858301306108134 x1]; 4c2e8d4/ELF/x86 [23 instructions / 17792519410809688294 x1]; 4c2e8d4/PE/x64 [22 instructions / 13266858301306108134 x1]; 4c2e8d4/PE/x86 [24 instructions / 17971593305574895999 x1].
type:.hash.M1K3S: 4c2e8d4/ELF/x86 [23 instructions / 12152402087626361968 x1]; 4c2e8d4/PE/x86 [24 instructions / 18355081188479622655 x1].
type:.hash.M1K7S: 4c2e8d4/ELF/x64 [22 instructions / 5768723426915729118 x1]; 4c2e8d4/PE/x64 [22 instructions / 5768723426915729118 x1].
type:.hash.M2K2M22K2M20: 4c2e8d4/ELF/x86 [32 instructions / 9262081398312506069 x1]; 4c2e8d4/PE/x86 [33 instructions / 5090562220727808937 x1].
type:.hash.M2K6M26K6M24: 4c2e8d4/ELF/x64 [30 instructions / 6214764704850151248 x1]; 4c2e8d4/PE/x64 [30 instructions / 6214764704850151248 x1].
type:.hash.M4K4M24: 4c2e8d4/ELF/x64 [22 instructions / 10304046957199972840 x1]; 4c2e8d4/PE/x64 [22 instructions / 10304046957199972840 x1].
type:.hash.M8I: 4c2e8d4/ELF/x86 [22 instructions / 5863756673841369179 x1]; 4c2e8d4/PE/x86 [23 instructions / 11674271459852339746 x1].
type:.hash.SM4SM4: 4c2e8d4/ELF/x86 [36 instructions / 5513473520240323125 x1]; 4c2e8d4/PE/x86 [37 instructions / 12267083270843038188 x1].
type:.hash.SM8: 4c2e8d4/ELF/x64 [22 instructions / 8122655181774796643 x1]; 4c2e8d4/PE/x64 [22 instructions / 8122655181774796643 x1].
type:.hash.SS: 4c2e8d4/ELF/x64 [22 instructions / 8122655181774796643 x1]; 4c2e8d4/ELF/x86 [22 instructions / 5863756673841369179 x1]; 4c2e8d4/PE/x64 [22 instructions / 8122655181774796643 x1]; 4c2e8d4/PE/x86 [23 instructions / 11674271459852339746 x1].
type:.hash.SSSM1: 4c2e8d4/ELF/x64 [33 instructions / 7059873393258587048 x1]; 4c2e8d4/ELF/x86 [37 instructions / 10827104472937793419 x1]; 4c2e8d4/PE/x64 [33 instructions / 7059873393258587048 x1]; 4c2e8d4/PE/x86 [38 instructions / 2310258023944104374 x1].
type:.hash.[20SM4SM4]: 4c2e8d4/ELF/x86 [24 instructions / 10603813338736674098 x1]; 4c2e8d4/PE/x86 [25 instructions / 7248689699186757434 x1].
type:.hash.[40SM8]: 4c2e8d4/ELF/x64 [28 instructions / 15478168688065061282 x1]; 4c2e8d4/PE/x64 [28 instructions / 15478168688065061282 x1].

Unassigned unnamed body hashes, grouped by instruction count and PicHash:
4c2e8d4/ELF/x64: 1 instructions / 1253497258561142223 x21; 2 instructions / 709328543774431377 x1; 2 instructions / 1199474625082419466 x1; 2 instructions / 1871952784396422270 x1; 2 instructions / 3884278758044570338 x1; 2 instructions / 4747975822881892076 x1; 2 instructions / 7848248245381482090 x1; 2 instructions / 12845510849829390021 x1; 2 instructions / 14813712564013249873 x1; 2 instructions / 15300834253427406105 x1; 2 instructions / 17757818480033663776 x1; 3 instructions / 13946078543747686057 x1; 4 instructions / 466242121924152354 x7; 4 instructions / 479733866372137785 x5; 4 instructions / 484883878456952342 x1; 4 instructions / 1013815919982788693 x3; 4 instructions / 1859265969517573294 x7; 4 instructions / 1875332132825442534 x1; 4 instructions / 1892339260696689440 x5; 4 instructions / 2787472059569828029 x5; 4 instructions / 2883509597375973843 x1; 4 instructions / 3013140126532281450 x1; 4 instructions / 3938064974853496746 x1; 4 instructions / 4279976378107065028 x5; 4 instructions / 4984615481160508625 x11; 4 instructions / 6061177580974932870 x2; 4 instructions / 7087688945512651782 x4; 4 instructions / 7502415358178069368 x14; 4 instructions / 7853116755074293593 x2; 4 instructions / 7868796672815418340 x4; 4 instructions / 8186478683960583943 x2; 4 instructions / 8669918230834686104 x1; 4 instructions / 9153990811541768343 x5; 4 instructions / 9321031006858790252 x5; 4 instructions / 9533150250430668979 x1; 4 instructions / 9719117887885905362 x1; 4 instructions / 10066247772650805021 x1; 4 instructions / 10209695728725523735 x6; 4 instructions / 11681835560179413006 x23; 4 instructions / 12810410087438975592 x5; 4 instructions / 12971503647171835083 x2; 4 instructions / 13603197538284953380 x13; 4 instructions / 15362268661448520171 x7; 4 instructions / 15863342506519189091 x3; 4 instructions / 16354389200395211204 x9; 4 instructions / 16838229569466124796 x3; 4 instructions / 17986230230947536065 x1; 4 instructions / 18123910285422118736 x1; 4 instructions / 18137333673977191221 x1; 4 instructions / 18293057715955751665 x1; 4 instructions / 18430194353520939746 x1; 5 instructions / 154967920570359517 x1; 5 instructions / 366702057425217099 x1; 5 instructions / 1125328455349597092 x1; 5 instructions / 1135592924879421061 x1; 5 instructions / 1223357447902681308 x1; 5 instructions / 1330577509584776654 x1; 5 instructions / 1725229871985651643 x1; 5 instructions / 2454876327293401546 x1; 5 instructions / 3103619966475620767 x1; 5 instructions / 3284158718899958424 x1; 5 instructions / 3779508555681533950 x4; 5 instructions / 3799733174648122994 x1; 5 instructions / 4197113218982899565 x1; 5 instructions / 4225881530500251430 x1; 5 instructions / 4639065803380970828 x2; 5 instructions / 4860551205229623613 x1; 5 instructions / 4900059630170596257 x1; 5 instructions / 4938649370073764499 x1; 5 instructions / 4966339586193846480 x1; 5 instructions / 5000614911285288592 x2; 5 instructions / 5009503425069593959 x1; 5 instructions / 5177680512814794749 x1; 5 instructions / 5633823767421733937 x2; 5 instructions / 6008378221450384125 x1; 5 instructions / 6344060107305919991 x1; 5 instructions / 7213365040749744696 x1; 5 instructions / 7502951754183821399 x1; 5 instructions / 8704764822672478247 x1; 5 instructions / 9205758047771843464 x1; 5 instructions / 9334153320530220531 x1; 5 instructions / 9557524277516235582 x1; 5 instructions / 9604082667688595145 x1; 5 instructions / 10617736855259120934 x1; 5 instructions / 11390828028689059997 x1; 5 instructions / 11780952251194000847 x1; 5 instructions / 11957290731441088956 x1; 5 instructions / 12402281548247848465 x3; 5 instructions / 12805814178794771891 x1; 5 instructions / 13145741522110397009 x1; 5 instructions / 13590727620943397304 x1; 5 instructions / 14193606833757703293 x3; 5 instructions / 14347329795412147282 x7; 5 instructions / 14440546000522779065 x3; 5 instructions / 15351946437811260401 x1; 5 instructions / 15520134055667118817 x1; 5 instructions / 15579897228816817821 x5; 5 instructions / 15622839617200227752 x1; 5 instructions / 15755742389662141705 x1; 5 instructions / 16166709459672700644 x1; 5 instructions / 16495335239287670572 x1; 5 instructions / 16706381929652121450 x1; 5 instructions / 16720566162348762174 x1; 5 instructions / 17126181692089012572 x1; 5 instructions / 17312016199869158575 x1; 5 instructions / 17417984021366440729 x1; 6 instructions / 61555360339899492 x1; 6 instructions / 191643017411608222 x1; 6 instructions / 271434280110956617 x1; 6 instructions / 529310756550246495 x10; 6 instructions / 761963754750419391 x1; 6 instructions / 903637983398037046 x1; 6 instructions / 1112499388210404705 x2; 6 instructions / 1646961245807967752 x1; 6 instructions / 1764594154248356300 x1; 6 instructions / 1844479024253806809 x1; 6 instructions / 2367491526284631912 x1; 6 instructions / 2442856041070810483 x1; 6 instructions / 2486914481780698110 x1; 6 instructions / 2490598027228342873 x1; 6 instructions / 2504353603206467546 x1; 6 instructions / 2509076424794489289 x1; 6 instructions / 2846584053266951815 x1; 6 instructions / 3175206845680805585 x3; 6 instructions / 3223630818360999593 x4; 6 instructions / 3724584505772185471 x3; 6 instructions / 4200792311004472669 x2; 6 instructions / 4407937756093166262 x1; 6 instructions / 4464792539574615235 x1; 6 instructions / 4467442484345121306 x1; 6 instructions / 5106169671663322836 x1; 6 instructions / 5355375799171272943 x1; 6 instructions / 5461567821434154800 x1; 6 instructions / 5512731596725224789 x1; 6 instructions / 5775979658101663382 x1; 6 instructions / 5851994480517348020 x3; 6 instructions / 6296295560287798570 x1; 6 instructions / 6368654904896549334 x1; 6 instructions / 6863038394419935440 x2; 6 instructions / 7139001992485243735 x1; 6 instructions / 7253328222508259097 x1; 6 instructions / 7278599577371131806 x2; 6 instructions / 7358520692331159354 x1; 6 instructions / 7359397886413699633 x1; 6 instructions / 8178447194314469511 x1; 6 instructions / 8461196563161074482 x1; 6 instructions / 8494510961748094570 x1; 6 instructions / 8676403454029464407 x1; 6 instructions / 8891340561615791907 x1; 6 instructions / 9233468830138433373 x3; 6 instructions / 9451945176127136378 x1; 6 instructions / 9884529853009278175 x1; 6 instructions / 10443800258177688297 x1; 6 instructions / 10968533542341539499 x1; 6 instructions / 11046651369087534381 x1; 6 instructions / 11269919806322353105 x1; 6 instructions / 11546672710070700530 x1; 6 instructions / 11647200428707653075 x1; 6 instructions / 11683070039438677303 x1; 6 instructions / 11791602359141297814 x1; 6 instructions / 12265522125535873049 x1; 6 instructions / 12898719129524577649 x1; 6 instructions / 13107328606678289101 x3; 6 instructions / 13313862135317693115 x2; 6 instructions / 13326909353186686218 x1; 6 instructions / 13463356710085548924 x1; 6 instructions / 13880835249858507508 x1; 6 instructions / 14005410772488361254 x2; 6 instructions / 14046535682021536100 x1; 6 instructions / 14569438887296488991 x4; 6 instructions / 15245963201530196331 x4; 6 instructions / 15703788047371101426 x1; 6 instructions / 15763290850471995878 x1; 6 instructions / 15942310374684659100 x1; 6 instructions / 16063919820169720848 x1; 6 instructions / 16170227584865880309 x1; 6 instructions / 16172387864298395898 x4; 6 instructions / 16246074888035641638 x3; 6 instructions / 16354570385847191929 x1; 6 instructions / 16398570293026497814 x1; 6 instructions / 16421191169512054161 x1; 6 instructions / 16445812180235432919 x1; 6 instructions / 16563029019218511984 x1; 6 instructions / 16634384284947514637 x1; 6 instructions / 16849592603592083643 x1; 6 instructions / 17654951975750415535 x1; 6 instructions / 17772550083822630892 x1; 6 instructions / 17810899713073381535 x1; 6 instructions / 17886764374563932321 x1; 6 instructions / 18138979090343181301 x1; 6 instructions / 18231096991964672141 x1; 6 instructions / 18415573699761743854 x4; 7 instructions / 37206039712859630 x1; 7 instructions / 547204761162953327 x1; 7 instructions / 655304754569287314 x1; 7 instructions / 749424685618735238 x1; 7 instructions / 960545615014987633 x1; 7 instructions / 1073836925256776989 x1; 7 instructions / 2237216855045386695 x1; 7 instructions / 2299433246358833665 x1; 7 instructions / 2688618726905090981 x1; 7 instructions / 3433802018245850523 x1; 7 instructions / 3459935859169780032 x1; 7 instructions / 3571799067639899370 x1; 7 instructions / 4481632147123559025 x1; 7 instructions / 4648866347924919283 x1; 7 instructions / 4717549287516603508 x1; 7 instructions / 4882546931001919022 x1; 7 instructions / 5068045291200079974 x1; 7 instructions / 5173328888599911806 x1; 7 instructions / 5698992294584790916 x1; 7 instructions / 5910963698928634632 x1; 7 instructions / 6923941324073959918 x1; 7 instructions / 7411198654196710362 x2; 7 instructions / 7530660163297903876 x1; 7 instructions / 7720972985909910717 x1; 7 instructions / 7865887130536132609 x1; 7 instructions / 8263146232085316721 x1; 7 instructions / 8542457409318616168 x1; 7 instructions / 8790165119293723201 x1; 7 instructions / 8960030625319440725 x1; 7 instructions / 9484819655714160709 x1; 7 instructions / 9875900010215031567 x1; 7 instructions / 10134566135100105948 x1; 7 instructions / 10172205089056719167 x1; 7 instructions / 10490488339006186658 x1; 7 instructions / 11010546444076766461 x1; 7 instructions / 11047170045453597504 x1; 7 instructions / 11215338326742232820 x1; 7 instructions / 12776575910955480953 x1; 7 instructions / 13918204302111358100 x1; 7 instructions / 13984717841331877162 x1; 7 instructions / 14064948455979132832 x1; 7 instructions / 14099840612751665210 x1; 7 instructions / 14256109905585104718 x2; 7 instructions / 14645704214249969005 x1; 7 instructions / 14693901650980826732 x1; 7 instructions / 15181059257898227276 x1; 7 instructions / 15294404414615123411 x1; 7 instructions / 15308368956800126666 x1; 7 instructions / 15788885404396791447 x1; 7 instructions / 16148823825727529090 x1; 7 instructions / 16348267902935945254 x1; 7 instructions / 17189904771706946531 x1; 7 instructions / 17460915838186392487 x2; 7 instructions / 18314017324665239815 x1; 8 instructions / 109576239853371360 x1; 8 instructions / 734583267590303144 x1; 8 instructions / 2930727492099141652 x1; 8 instructions / 4123815098752016881 x1; 8 instructions / 5345380756543007010 x1; 8 instructions / 7615380982592124911 x1; 8 instructions / 8212583642833327160 x1; 8 instructions / 9035888150348148890 x1; 8 instructions / 9525973269839879205 x1; 8 instructions / 10756028836623349164 x1; 8 instructions / 11741008204523607690 x1; 8 instructions / 12044516374410781753 x1; 8 instructions / 12294238456338052941 x1; 8 instructions / 14295106658759117286 x1; 8 instructions / 14437637856981020939 x1; 8 instructions / 16420901296994827744 x1; 8 instructions / 16987319468875184160 x1; 9 instructions / 555842740949125584 x1; 9 instructions / 5206453098736190098 x1; 9 instructions / 6259333573965293706 x1; 9 instructions / 7773016938219117709 x1; 9 instructions / 7983006867926374318 x1; 9 instructions / 8313049161975110375 x1; 9 instructions / 11691745524438815677 x1; 9 instructions / 12248161271697687233 x2; 9 instructions / 13813215450633519592 x1; 9 instructions / 14336406508004005987 x1; 10 instructions / 800169083007653836 x1; 10 instructions / 1510226614788711831 x1; 10 instructions / 5925983090846076670 x1; 10 instructions / 10733415820549342252 x1; 10 instructions / 11295748517761635247 x1; 10 instructions / 14426705181665618735 x1; 11 instructions / 629211881482081766 x1; 11 instructions / 1896598812245343859 x1; 11 instructions / 13762920082303646548 x1; 12 instructions / 5816845375264161560 x1; 12 instructions / 12117625941213303427 x1; 12 instructions / 17892800042589399487 x1; 13 instructions / 11313324718621946943 x1; 15 instructions / 7618519444701172540 x1; 168 instructions / 802665843768066461 x1.
4c2e8d4/ELF/x86: 1 instructions / 1253497258561142223 x21; 2 instructions / 709328543774431377 x1; 3 instructions / 148401315777280722 x1; 3 instructions / 399160679514267668 x8; 3 instructions / 976359947437822157 x5; 3 instructions / 1147611072075888476 x1; 3 instructions / 1311846981026947618 x1; 3 instructions / 1398177611179361221 x6; 3 instructions / 2056131248170849056 x4; 3 instructions / 2097594478084027413 x1; 3 instructions / 2223093078997474672 x26; 3 instructions / 2543126673818691657 x13; 3 instructions / 2984236938415076628 x10; 3 instructions / 3219571584817370776 x1; 3 instructions / 3231221364638622349 x1; 3 instructions / 3614492814838077920 x3; 3 instructions / 4163481402802604701 x2; 3 instructions / 4460970799201115503 x2; 3 instructions / 4691194224724853892 x27; 3 instructions / 4894112106753972222 x4; 3 instructions / 4990884184229136202 x3; 3 instructions / 5230879652179905945 x1; 3 instructions / 5411627868933477166 x6; 3 instructions / 6057988224881723664 x13; 3 instructions / 6124129502837219431 x1; 3 instructions / 6643155252630924153 x1; 3 instructions / 6686182100111529099 x2; 3 instructions / 6751922466082950787 x1; 3 instructions / 6780510416667428038 x2; 3 instructions / 7070597107886394599 x3; 3 instructions / 7093119332817302620 x1; 3 instructions / 7482789331876322950 x1; 3 instructions / 8482476970699413162 x7; 3 instructions / 8686872467240596747 x9; 3 instructions / 9271478335628820730 x14; 3 instructions / 9298730407441234007 x1; 3 instructions / 9300006949116477056 x15; 3 instructions / 9661926108177997337 x8; 3 instructions / 9880003288711333562 x4; 3 instructions / 9891419357315307613 x1; 3 instructions / 10023930457628234326 x1; 3 instructions / 10262026747242345911 x12; 3 instructions / 10710683015193198486 x1; 3 instructions / 10862753617360190730 x1; 3 instructions / 11168194476536647249 x2; 3 instructions / 11249493185319714294 x1; 3 instructions / 11283242297261900764 x4; 3 instructions / 11373035793899285323 x2; 3 instructions / 11386804724158692021 x1; 3 instructions / 11505707742099716124 x1; 3 instructions / 11566145874295248281 x1; 3 instructions / 11987234206407536982 x5; 3 instructions / 12080723579987328256 x10; 3 instructions / 12080911748820801686 x1; 3 instructions / 12257594617881724567 x1; 3 instructions / 12317591906350599580 x9; 3 instructions / 12330679368504070167 x3; 3 instructions / 12392015734922357475 x1; 3 instructions / 12685759309273614150 x6; 3 instructions / 13212311453342307577 x8; 3 instructions / 13246477673380507206 x43; 3 instructions / 13434510762705549560 x17; 3 instructions / 13599064628811367293 x7; 3 instructions / 13837358998477261647 x1; 3 instructions / 14260648328560303049 x4; 3 instructions / 14518102167241501927 x1; 3 instructions / 14533286328495915255 x8; 3 instructions / 14757633970117164314 x2; 3 instructions / 14908812532638936722 x8; 3 instructions / 15314168636012089174 x1; 3 instructions / 15535549890465506758 x1; 3 instructions / 15627060837209997353 x1; 3 instructions / 15821737291407694269 x1; 3 instructions / 15919409915774540806 x3; 3 instructions / 15973662865982510727 x2; 3 instructions / 16125528404544653966 x1; 3 instructions / 16415083257577379761 x13; 3 instructions / 16954392341414018250 x16; 3 instructions / 17580311856940966838 x18; 3 instructions / 17629198399867309994 x1; 3 instructions / 17760685335412217700 x17; 3 instructions / 17770272309918310604 x1; 3 instructions / 17781062044293215487 x2; 3 instructions / 17826775624757932097 x2; 3 instructions / 18207159431037260881 x6.
4c2e8d4/PE/x64: none.
4c2e8d4/PE/x86: 3 instructions / 41953557743163579 x1; 3 instructions / 148401315777280722 x1; 3 instructions / 399160679514267668 x11; 3 instructions / 976359947437822157 x4; 3 instructions / 1311846981026947618 x1; 3 instructions / 1398177611179361221 x5; 3 instructions / 1645609012848902411 x1; 3 instructions / 2056131248170849056 x4; 3 instructions / 2097594478084027413 x1; 3 instructions / 2223093078997474672 x24; 3 instructions / 2543126673818691657 x11; 3 instructions / 2984236938415076628 x15; 3 instructions / 3219571584817370776 x1; 3 instructions / 3231221364638622349 x1; 3 instructions / 3526000115467055623 x1; 3 instructions / 3579864658959161819 x1; 3 instructions / 3614492814838077920 x4; 3 instructions / 3911644620111000156 x1; 3 instructions / 4163481402802604701 x2; 3 instructions / 4460970799201115503 x2; 3 instructions / 4691194224724853892 x22; 3 instructions / 4894112106753972222 x4; 3 instructions / 4990884184229136202 x3; 3 instructions / 5230879652179905945 x1; 3 instructions / 5411627868933477166 x6; 3 instructions / 6057988224881723664 x17; 3 instructions / 6124129502837219431 x1; 3 instructions / 6643155252630924153 x1; 3 instructions / 6686182100111529099 x3; 3 instructions / 6751922466082950787 x2; 3 instructions / 6780510416667428038 x1; 3 instructions / 7070597107886394599 x3; 3 instructions / 7093119332817302620 x1; 3 instructions / 7482789331876322950 x1; 3 instructions / 8482476970699413162 x9; 3 instructions / 8686872467240596747 x9; 3 instructions / 9271478335628820730 x14; 3 instructions / 9298730407441234007 x1; 3 instructions / 9300006949116477056 x14; 3 instructions / 9661207375846097140 x1; 3 instructions / 9661926108177997337 x11; 3 instructions / 9880003288711333562 x3; 3 instructions / 9891419357315307613 x1; 3 instructions / 10023930457628234326 x1; 3 instructions / 10262026747242345911 x11; 3 instructions / 11168194476536647249 x2; 3 instructions / 11249493185319714294 x1; 3 instructions / 11283242297261900764 x3; 3 instructions / 11373035793899285323 x1; 3 instructions / 11386804724158692021 x1; 3 instructions / 11505707742099716124 x1; 3 instructions / 11566145874295248281 x2; 3 instructions / 11987234206407536982 x5; 3 instructions / 12080723579987328256 x9; 3 instructions / 12080911748820801686 x1; 3 instructions / 12257594617881724567 x1; 3 instructions / 12317591906350599580 x8; 3 instructions / 12330679368504070167 x3; 3 instructions / 12392015734922357475 x1; 3 instructions / 12414849514400867290 x1; 3 instructions / 12685759309273614150 x9; 3 instructions / 13212311453342307577 x7; 3 instructions / 13246477673380507206 x42; 3 instructions / 13434510762705549560 x17; 3 instructions / 13599064628811367293 x5; 3 instructions / 14260648328560303049 x4; 3 instructions / 14518102167241501927 x1; 3 instructions / 14533286328495915255 x8; 3 instructions / 14757633970117164314 x2; 3 instructions / 14908812532638936722 x8; 3 instructions / 15314168636012089174 x1; 3 instructions / 15627060837209997353 x1; 3 instructions / 15821737291407694269 x1; 3 instructions / 15919409915774540806 x3; 3 instructions / 15973662865982510727 x1; 3 instructions / 16125528404544653966 x1; 3 instructions / 16415083257577379761 x12; 3 instructions / 16954392341414018250 x15; 3 instructions / 17580311856940966838 x16; 3 instructions / 17629198399867309994 x1; 3 instructions / 17760685335412217700 x16; 3 instructions / 17770272309918310604 x1; 3 instructions / 17781062044293215487 x3; 3 instructions / 17826775624757932097 x2; 3 instructions / 18207159431037260881 x7.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


_PREPARE = r"""python - <<'PY'
from pathlib import Path
import os
import re
import shutil
import subprocess
assert subprocess.check_output(['go', 'version'], text=True).split()[2] == 'go1.27.3'
out = Path('corpus-analysis')
shutil.rmtree(out, ignore_errors=True)
entries = [p for p in Path('.').iterdir() if p.name not in ['.git', out.name]]
out.mkdir()
for p in entries:
    target = out / p.name
    if p.is_dir():
        shutil.copytree(p, target, copy_function=os.link, symlinks=True)
    else:
        os.link(p, target)
entry = out / 'implant/sliver/main.go'
assert 'func {{.}} ()' in entry.read_text()
entry.rename(entry.with_suffix('.go.disabled'))
changed = ['implant/sliver/main.go (excluded generated entry wrapper)']
for i, p in enumerate(sorted((out / 'implant/sliver').rglob('*.go'))):
    if p.name.endswith('_test.go'):
        continue
    old = p.read_text()
    new = re.sub(r'^func init\s*\(\s*\)', 'func corpusDisabledInit'+str(i)+'()', old, flags=re.M)
    if p == out / 'implant/sliver/runner/runner.go':
        if '{goos}' != 'windows':
            assert new.count('"golang.org/x/sys/windows/svc"') == 1
            new = new.replace('"golang.org/x/sys/windows/svc"', '')
            new = new.replace('type sliverService struct{}', '')
            start = new.index('func (serv *sliverService) Execute(')
            brace = new.index('{', start)
            depth, end = 1, brace + 1
            while depth:
                depth += (new[end] == '{') - (new[end] == '}')
                end += 1
            new = new[:start] + new[end:]
            new, count = re.subn(r'^\s*svc\.Run\(.*\)\s*$', '', new, flags=re.M)
            assert count == 1
        lines = []
        depth = selected = 0
        windows = '{goos}' == 'windows'
        keep = False
        for line in new.splitlines(keepends=True):
            match = re.search(r'\{\{\s*(.*?)\s*\}\}', line) if line.lstrip().startswith('//') else None
            directive = match.group(1).strip() if match else ''
            if not depth:
                if directive == 'if eq .Config.GOOS "windows"':
                    depth, keep = 1, windows
                    selected += 1
                    continue
                lines.append(line)
                continue
            if directive.startswith(('if ', 'range ', 'with ')):
                depth += 1
            elif directive == 'end':
                depth -= 1
                if not depth:
                    continue
            elif directive == 'else' and depth == 1:
                keep = not windows
                continue
            if keep:
                lines.append(line)
        assert depth == 0 and selected == 3
        new = ''.join(lines)
    if new != old:
        temp = p.with_suffix('.corpus-tmp')
        temp.write_text(new)
        temp.replace(p)
        changed.append(str(p.relative_to(out)))
(out / 'implant/sliver/corpus_main.go').write_text(
    'package main\nimport ("fmt"; "github.com/bishopfox/sliver/implant/sliver/runner")\n'
    'func main() { fmt.Printf("%p", runner.Main) }\n')
assert '{{.Build.PeerPrivateKey}}' in (out / 'implant/sliver/cryptography/implant.go').read_text()
print('Analysis-only changed files:', changed, flush=True)
PY"""


RECIPES = {
    'Sliver_4c2e8d4_go127_analysis': Recipe(
        family='Sliver', version='4c2e8d4-go1.27.3-analysis',
        upstream='https://github.com/BishopFox/sliver', license='GPL-3.0',
        source=Source(
            url='https://codeload.github.com/BishopFox/sliver/tar.gz/4c2e8d4bdac79eb7c22143d54f49025faac5d1e6',
            sha256='92b06e937e7ec443605daa2ac665d53c314db204c2136dd13a31ae331ca31fe5'),
        build=[BuildStep(_PREPARE, env={'GOTOOLCHAIN': 'local'}), BuildStep(
            'go build -mod=vendor -trimpath '
            '-gcflags=github.com/bishopfox/sliver/...=-l '
            '-o reference-sliver ./implant/sliver', cwd='corpus-analysis',
            env={'GOOS': '{goos}', 'GOARCH': '{goarch}',
                 'CGO_ENABLED': '0', 'GOTOOLCHAIN': 'local'})],
        artifacts=[Artifact(path='corpus-analysis/reference-sliver',
                            component='implant-analysis')],
        toolchains=['linux_x86', 'linux_x64', 'mingw_x86', 'mingw_x64'],
        requires=['go', 'python'], glue_filter='go',
        build_flags='Go 1.27.3; CGO_ENABLED=0 GOTOOLCHAIN=local; '
                    '-mod=vendor -trimpath '
                    '-gcflags=github.com/bishopfox/sliver/...=-l; '
                    'inert address-only main; disabled first-party init; '
                    'generated export wrapper excluded; target-OS dispatch '
                    'branches selected; Linux service adapter omitted',
        notes='Pinned Sliver source commit 4c2e8d4bdac79eb7c22143d54f49025faac5d1e6 '
              'and its source-controlled vendor tree, verified by archive SHA-256. '
              'Go 1.27.3 is the actual compiler, checked exactly. Only a hard-linked '
              'analysis copy is adapted with atomic replacement: exclude the '
              'unexpanded generated export wrapper, rename explicit first-party '
              'initializers, select existing target-OS branches and omit the '
              'Windows service adapter on Linux. An address-only main calls no '
              'implant function. All configuration, endpoint, certificate and '
              'key templates remain unexpanded. No operator profile, generator, '
              'server or compiled program is run. This is a non-operational '
              'reference image. Vendored functions remain and are reported '
              'separately from first-party namespace counts. Go 1.27 runtime '
              'reference data is not supplied by this contribution; runtime '
              'filtering uses package names. Platform ids describe containers.'),
}
