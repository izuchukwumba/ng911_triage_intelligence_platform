"""The pinned NENA EIDO profile this platform supports (design v1.2, section 3B.2).

Only one edition is supported, identified down to the git commit and the
sha256 of every schema file. Anything else is rejected as unsupported rather
than reinterpreted (version-lock policy, section 3B.2).

Licence note: the NENA911/EIDO-JSON repository publishes no licence file, so
its schema files are **not** copied into this repository. They are fetched
from the pinned commit at runtime and verified against the digests below
(see ``ntip.interop.eido.fetch``).
"""

from dataclasses import dataclass

ADAPTER_VERSION = "eido-adapter-0.2.0"


@dataclass(frozen=True)
class EidoProfile:
    profile_id: str
    standard_edition: str
    repository: str
    commit: str
    eido_version: str
    root_schema: str
    root_type: str
    files: dict[str, str]
    sample: tuple[str, str]

    def raw_url(self, path: str) -> str:
        return f"https://raw.githubusercontent.com/{self.repository}/{self.commit}/{path}"

    @property
    def schema_artifact_digest(self) -> str:
        """One digest over every pinned file, for manifests and reports."""
        import hashlib

        joined = "\n".join(f"{p}={d}" for p, d in sorted(self.files.items()))
        return "sha256:" + hashlib.sha256(joined.encode()).hexdigest()


PROFILE = EidoProfile(
    profile_id="ntip-eido-021.1b-import-v1",
    # NENA-STA-021.1b "Reissue" (August 2022), the latest published edition at
    # the time of pinning; NENA-STA-021.1.1 was still in public review.
    standard_edition="NENA-STA-021.1b",
    repository="NENA911/EIDO-JSON",
    commit="c3b8d2063be63d27ff7e2d3c353c597c71817a1b",
    eido_version="1.0",
    root_schema="Schema/openapi.yaml",
    root_type="EmergencyIncidentDataObjectType",
    files={
        "Schema/NIEMComponents/aamva_d20.yaml": "b2a669cfb3b5a5a7c9aaed719b68fe18559d79b675d5b7893f9b876a6d75bd9f",
        "Schema/NIEMComponents/apco.yaml": "6b972486cffff50792d2ccd525168697f9ab60d6265097fb061b2f09d32183dc",
        "Schema/NIEMComponents/biom.yaml": "ca9d8f6b8fd5d9cb68e8a0a454053c6d43edfd4f1048440b54c76fa0944ed044",
        "Schema/NIEMComponents/can.yaml": "f31420a4f7bba1d75e697836a7564d516148ecf99e8d27f92021eba2660812ba",
        "Schema/NIEMComponents/cbrn.yaml": "ded7781a39a238dc8c4260b0c92e2359a5c587f0410518e9d2f83acf36dad682",
        "Schema/NIEMComponents/cbrncl.yaml": "ce03e64f587ea24b77afb9b7dd7bafe96c0f7054d0433331902efcd58022dbe3",
        "Schema/NIEMComponents/census.yaml": "dd04c69295849b5e7bf9c7e8d3d6b6135bb8c2b06f148300b68513942149895c",
        "Schema/NIEMComponents/commodity.yaml": "8529405a2977a69494681314dea2ab8374434f6098dd01a0c0a4cc29b06cb092",
        "Schema/NIEMComponents/dea.yaml": "5fcfb4236f83630b45697cefa2502c15666a86017ba33029ed9d842071d43214",
        "Schema/NIEMComponents/dod_jcs-pub2.0.yaml": "6cde086a8d5f363b21772f78d83886d15d21c1d156a9afd62e75d193084518b3",
        "Schema/NIEMComponents/dol.yaml": "307b138135f614e5f85b1348171e6a3009341d3102697e1bfedaf4b1bb6f999b",
        "Schema/NIEMComponents/em.yaml": "44b37bad5b33b9d8a43ff8e1e97abf81a87d77aa14c9c5832ffc5a2286c393df",
        "Schema/NIEMComponents/fips_5-2.yaml": "8147ca6de877eeceeedd9ced48febaad222bb7cce61f0436ca967d53a92abd3e",
        "Schema/NIEMComponents/geo.yaml": "6174b720900d523a1b809ef902f344bddd0359d087ae83f38fcff061578c2174",
        "Schema/NIEMComponents/hazmat.yaml": "ff37d2d49ddf2a135a94d6bfed9402e483725eef68a0ccd229a4562dd07b7c38",
        "Schema/NIEMComponents/hl7.yaml": "ccf231623915f28a302b5529798403ab82e8be3e0615f044a9f4a0f6128ea430",
        "Schema/NIEMComponents/hs.yaml": "71424bca9b2565bba05a24728d5dcc9cc1905949bd85c5ba23956e24a52524db",
        "Schema/NIEMComponents/im.yaml": "4ff97762c102b58e5a1fd1b20a1de3bd5d9ca880f13471f11bfff1fd2edf0d7e",
        "Schema/NIEMComponents/intel.yaml": "d6059880f5d740b25fda6dd8bd2eb72f470543460570b5f72fdd1d434cc7ecd2",
        "Schema/NIEMComponents/iso_3166.yaml": "2ea6f326b02da501466f260172431c7f0af83ea7dccdad4587c420420449b7f6",
        "Schema/NIEMComponents/iso_4217.yaml": "544b01219276aadc04390ca7c63ba423d1428da0e1d7ed74c35a217ca277f6f1",
        "Schema/NIEMComponents/iso_639-3.yaml": "62ee00f4220e40efcb5346b9b36b78d55d98dc6c08350192100bc9d54098a3f7",
        "Schema/NIEMComponents/it.yaml": "5e4726f43a009ebad5b56501b9a4c8b790b89c26e5dc7be4f510832037260254",
        "Schema/NIEMComponents/itcodes.yaml": "159ac31111858d8d64bfdeb3d3bc6b0545c8bd6f79ba4cedfe052ee6a21c4679",
        "Schema/NIEMComponents/j.yaml": "f5b6645c01d24c7c3cb6da1569b6673d2309b05ff454a42ca2696232b3c626c6",
        "Schema/NIEMComponents/m.yaml": "83e6c1b274e55f87a8697b2710ddda80ac2141b9a1a88818ca8a2a2023201a26",
        "Schema/NIEMComponents/mmucc.yaml": "f26a1a29b4a681ea9339da6bd2f352aab3533f593c230185b3577c47e49f4120",
        "Schema/NIEMComponents/mo.yaml": "4f797fb767d0e0608d5993cb8d5774267f1f049625ad4aa7407b23aa1a00ed8e",
        "Schema/NIEMComponents/nc-4.0.1.yaml": "b102cb2065d72566977223018dff84e262ddd1ca1d0a0d940b9f81b1323f1c0e",
        "Schema/NIEMComponents/nc.yaml": "5d41665734bb5db9198b800b3db8d9f3ea6af041f26a1b79c8685f5bd51dbc7d",
        "Schema/NIEMComponents/ncic.yaml": "28874a8bca327a18ab02a0d77d4f489c7fde402cdc18f467bf35296899fc1433",
        "Schema/NIEMComponents/ndex.yaml": "ebd68fd8be2c1142685f845e3c5a2a4b58c57b6d8cfaa0b915c9432199d519d8",
        "Schema/NIEMComponents/nga.yaml": "b92f018a577883734046bf98a4ea65c32c198b9c7da3794f54cf4c6001e4b99f",
        "Schema/NIEMComponents/niem-xs.yaml": "43c4d406fe5ec34abcb82bb8236e9586589d593ff89eb1aed991f6a4fe63062d",
        "Schema/NIEMComponents/nlets.yaml": "75fbcc623ec0eeaf54af5bc78ba8fc0d1d11050fd129a82ce0e781f742af6f36",
        "Schema/NIEMComponents/occs.yaml": "f61bd8ab95285306a9e0315170a7fc76e0e4eadd3369c81a206286d956101657",
        "Schema/NIEMComponents/sar.yaml": "557d8efe74e57bcec9c82b41140d3a40d9f03bf76b607ef47eff9d165623f399",
        "Schema/NIEMComponents/scr.yaml": "e621c9e5667a76da48cc249c9a1c98702fe91bdf1b058f3859a111327af468a2",
        "Schema/NIEMComponents/st.yaml": "b475d6cd0216b6954c6c2becabf8b86d4f54b8a2e868f053c7164d21e739b715",
        "Schema/NIEMComponents/ucr.yaml": "657c277785a360424c26e0f04beaca9747c009594e1586eec02da58e40dd2494",
        "Schema/NIEMComponents/unece.yaml": "de606dabdf7627dd6f9bda2534a0cbb1a921e816293b02628a02afb5e54394bb",
        "Schema/NIEMComponents/usps.yaml": "71fa4ed6f015e16d1067870a9cf43ae7fd6bdd0348b5494d2a497252f85cd233",
        "Schema/NIEMComponents/xCard.yaml": "5788a8b60791dc73ae4d9189b03f9ccf2d256978eaf4ee7b2e06493ccd687777",
        "Schema/openapi.yaml": "a13a338597e8eeab89e61aac5ef3a78c64dfe200fde158f7d06b5fe6cc67a61f",
    },
    sample=(
        "Samples/Sample call transfer EIDO.json",
        "4f98a553e6e095e25c96a377a068c18ea87fe1674c65199f9a2f7afe0d5bf57d",
    ),
)
