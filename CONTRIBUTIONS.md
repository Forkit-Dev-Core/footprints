# How the Forkit open-source community built this

Forkit Core began with [Syed Amir Hamza](https://github.com/syedofc) and [Arpita Sarker](https://github.com/arpitasarker01). Its [first public commit](https://github.com/Forkit-Dev-Core/Forkit_Dev/commit/f206626) introduced the engine for creating and verifying AI Passports. Footprints made that engine usable from a local app. Contributors then added live device discovery, made lineage and verification more reliable, and showed how to review observations from local and cloud runs. Thank you to everyone who built, tested, reviewed, and explained the work along the way.

## From the first Core commit to Footprints

| Contributor | What they made possible |
| --- | --- |
| [Arpita Sarker](https://github.com/arpitasarker01) | Added framework adapters and self-hosted sync, then started Footprints and connected it to Core for model Passport creation and verification. [Core #1](https://github.com/Forkit-Dev-Core/Forkit_Dev/pull/1) · [Core #6](https://github.com/Forkit-Dev-Core/Forkit_Dev/pull/6) · [Footprints #4](https://github.com/Forkit-Dev-Core/footprints/pull/4) |
| [Syed Amir Hamza](https://github.com/syedofc) | Built the portable Windows download, integrated Shahbaz’s live discovery into it, and added checks that link the downloaded ZIP to the GitHub build that produced it. [Footprints #6](https://github.com/Forkit-Dev-Core/footprints/pull/6) · [Footprints #8](https://github.com/Forkit-Dev-Core/footprints/pull/8) · [Footprints #10](https://github.com/Forkit-Dev-Core/footprints/pull/10) |
| [Muhammad Shahbaz](https://github.com/khawajashahbaz) | Built live device and repository discovery, plus Passport creation for supported AI tools and agent setups. His original commits shipped in the Windows preview through #10. [Footprints #7](https://github.com/Forkit-Dev-Core/footprints/pull/7) · [Footprints #10](https://github.com/Forkit-Dev-Core/footprints/pull/10) |

## Making Core and discovery more reliable

| Contributor | What they made possible |
| --- | --- |
| [Sneha P Pratap](https://github.com/snehaapratap) | Made deep lineage chains traversable without hitting Python’s recursion limit. [Core #17](https://github.com/Forkit-Dev-Core/Forkit_Dev/pull/17) |
| [Harsh Raj Singhania](https://github.com/HarshRajSinghania) | Fixed Passport verification so valid uppercase artifact hashes are accepted and malformed hashes are rejected. [Uppercase hash fix](https://github.com/Forkit-Dev-Core/Forkit_Dev/commit/e8e476187193b09e80737dcd4c85bfa8c2624f86) · [Malformed hash fix](https://github.com/Forkit-Dev-Core/Forkit_Dev/commit/c01ce82f0a7927e8ae8a793ad78338f89cf24718) |
| [Doomguy-BFG9000](https://github.com/Doomguy-BFG9000) | Tightened version validation while keeping legacy records inspectable, and made lineage reject invalid graphs and return clearer CLI results. [Core #20](https://github.com/Forkit-Dev-Core/Forkit_Dev/pull/20) · [#21](https://github.com/Forkit-Dev-Core/Forkit_Dev/pull/21) · [#22](https://github.com/Forkit-Dev-Core/Forkit_Dev/pull/22) · [#23](https://github.com/Forkit-Dev-Core/Forkit_Dev/pull/23) |
| [Aditya Singh Bakawat (CyberKun)](https://github.com/CyberKun) | Added regression tests so duplicate runtime and model-file signals produce one finding apiece while retaining the evidence count. [Footprints #15](https://github.com/Forkit-Dev-Core/footprints/pull/15) |

## Work in review and contributor prototypes

| Contributor | What they contributed |
| --- | --- |
| [Muhammad Afzaal Afzal](https://github.com/M-Afzaal-Afzal) | Proposed showing why each discovery result appeared and added tests for timestamp validation. The proposal is still in review. [Footprints #5](https://github.com/Forkit-Dev-Core/footprints/pull/5) |
| [K S Neeraj](https://github.com/Neeraj111010) | Implemented lookup by a unique Passport ID prefix. The follow-up PR carries his original commit and remains open. [Core #19](https://github.com/Forkit-Dev-Core/Forkit_Dev/pull/19) · [Core #29](https://github.com/Forkit-Dev-Core/Forkit_Dev/pull/29) |
| [Udan M](https://github.com/UdanM) | Built the agent audit prototype and a local-PC/cloud-VM workflow for comparing observed activity. [Original prototype](https://github.com/UdanM/forkit-agent-audit/commit/3f5b2aaead433a5bda7b9bbfbbc1583064da27d0) · [Two-host implementation](https://github.com/UdanM/forkit-agent-audit/commit/6de06a8) |
| [Eren Mutlu](https://github.com/eren-mutlu) | Built AutoDiscover and integrated Udan’s audit work into its discovery and activity views, including checks that leave ambiguous activity unattributed. [AutoDiscover](https://github.com/eren-mutlu/forkit-autodiscover-hackathon) · [Attribution implementation](https://github.com/eren-mutlu/forkit-autodiscover-hackathon/commit/ca726e5) · [Technical merge brief](https://github.com/UdanM/forkit-agent-audit/blob/67a08cb7b826103dc7d829c38a29927dbb570dae/docs/MERGE_BRIEF.md) |

Udan and Eren’s work gives Footprints a starting point for reviewing local and cloud observations under one Passport. That integration is proposed. The contributor prototype is available to try today. [AutoDiscover walkthrough](https://github.com/UdanM/forkit-agent-audit#demo-walkthrough)

## Help shape the next release

Try the preview, report what you observe using synthetic examples, or tell us if a contribution is missing from this page. Testing, documentation, issue reports, and reviews all help the project improve. When we adapt a contribution, we thank its authors, link the original work, and say what shipped. [Footprints community guide](https://github.com/Forkit-Dev-Core/footprints/blob/main/docs/community.md) · [Preview testing](https://github.com/Forkit-Dev-Core/footprints/issues/14) · [Core issues](https://github.com/Forkit-Dev-Core/Forkit_Dev/issues)
