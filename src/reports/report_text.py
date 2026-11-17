"""
report_text.py
--------------
Full academic text for:
'Palaeoclimate Stability and Modern Biodiversity: Methodological Resolution of Spatial Autocorrelation, Macroecological Ceilings, and Taxonomic Divergence'

Authors:
Mani Bhavana (2024101053) [sirnelli.bhavana@students.iiit.ac.in]
Charishma Gaddampally (2024101097) [charishmagaddampally@gmail.com]
Mokshitha Mokthum (2024101059) [mokthum.mokshitha@students.iiit.ac.in]
Veekshita Sai (2024102026) [veekshita.sai@students.iiit.ac.in]

Affiliation:
Lab for Spatial Informatics, International Institute of Information Technology, Hyderabad (IIIT-Hyderabad),
Gachibowli, Hyderabad, Telangana, 500032, India.
*Corresponding author: Charishma Gaddampally (charishmagaddampally@gmail.com)
"""

TITLE = "Quaternary Palaeoclimate Velocity and Modern Terrestrial Biodiversity: Methodological Resolution of Spatial Autocorrelation, Macroecological Ceilings, and Taxonomic Divergence"

AUTHORS = [
    {"name": "Mani Bhavana", "roll": "2024101053", "email": "sirnelli.bhavana@students.iiit.ac.in", "affiliation": "1"},
    {"name": "Charishma Gaddampally", "roll": "2024101097", "email": "charishmagaddampally@gmail.com", "affiliation": "1*", "is_corresponding": True},
    {"name": "Mokshitha Mokthum", "roll": "2024101059", "email": "mokthum.mokshitha@students.iiit.ac.in", "affiliation": "1"},
    {"name": "Veekshita Sai", "roll": "2024102026", "email": "veekshita.sai@students.iiit.ac.in", "affiliation": "1"}
]

AFFILIATION_TEXT = "Lab for Spatial Informatics, International Institute of Information Technology - Hyderabad, Gachibowli, Hyderabad, Telangana, 500032, India."

CORRESPONDING_TEXT = (
    "Charishma Gaddampally\n"
    "Lab for Spatial Informatics, IIIT-Hyderabad, Gachibowli, Hyderabad, Telangana, 500032, India\n"
    "Email: charishmagaddampally@gmail.com; sirnelli.bhavana@students.iiit.ac.in"
)

# -----------------------------------------------------------------------------
# ABSTRACT (Target: 150 - 200 words)
# -----------------------------------------------------------------------------
ABSTRACT_TEXT = (
    "Whether modern biodiversity-rich regions reflect long-term Quaternary climate stability remains contentious in macroecology. "
    "We evaluate global terrestrial vertebrate distributions across 755 5° and 4,395 2° grid cells using PaleoClim (CHELSA) "
    "and WorldClim (CCSM4) surfaces from the Last Glacial Maximum (~21 ka) to the present. While uncorrected linear regressions suggest "
    "a negative relationship between instability and richness (partial rho = -0.258 to -0.284, p < 0.001), spatial auditing reveals "
    "severe confounding by spatial autocorrelation (Moran's I = 0.20-0.25), latitudinal collinearity (VIF = 1.97), and boundary leakage. "
    "We implement five methodological extensions: spatial eigenvector mapping, training-only orthogonalization, 1,000 km buffered cross-validation, "
    "stochastic frontier analysis, and hierarchical multi-taxa modeling. Orthogonalizing stability eliminates collinearity (VIF = 1.00) "
    "and collapses non-linear tree gains by 66%. Stochastic frontier analysis reveals that 97.8% of residual variance represents "
    "ecological shortfall below an energetic ceiling, where climate velocity exerts no constraint (beta = -0.0193, p = 0.384). "
    "Hierarchical models reject uniform sensitivity (chi-squared = 53.74, p < 10^-11): reptiles exhibit pronounced vulnerability "
    "(beta = -0.2270, p < 10^-4), whereas amphibians decouple entirely (beta = +0.0438, p = 0.2513). Rather than a monolithic driver, "
    "historical stability operates as a taxon-specific physiological constraint and an endemism filter."
)

KEYWORDS_TEXT = "Palaeoclimate stability; Quaternary climate velocity; Species richness; Macroecological ceilings; Spatial autocorrelation; Stochastic Frontier Analysis"

# -----------------------------------------------------------------------------
# 1. INTRODUCTION (Target: 1,000 - 1,200 words)
# -----------------------------------------------------------------------------
INTRO_PARAGRAPHS = [
    (
        "The uneven geographic distribution of life on Earth represents one of the most prominent and enduring phenomena in the natural "
        "sciences. Across continents, biomes, and taxonomic lineages, species richness exhibits profound spatial disparities that have "
        "captivated evolutionary biologists and macroecologists since the pioneering observations of Alexander von Humboldt and Alfred Russel "
        "Wallace (Currie 1991; Jetz et al. 2012). While contemporary environmental energy, precipitation availability, and topographic "
        "heterogeneity are universally acknowledged as primary proximal drivers of modern species distributions (Hawkins et al. 2003), "
        "contemporary conditions alone frequently prove insufficient to fully account for observed diversity gradients, high regional "
        "endemism, and disparate taxonomic assemblages across distinct biogeographical realms (Araújo et al. 2008; Svenning et al. 2015). "
        "Consequently, an influential macroevolutionary paradigm—the palaeoclimate stability hypothesis—posits that contemporary biodiversity "
        "hotspots are disproportionately concentrated in geographical regions characterized by long-term climatic persistence throughout the "
        "Quaternary epoch, spanning glacial-interglacial cycles from the Last Glacial Maximum (LGM, ~21,000 years before present) to the current "
        "interglacial period (Sandel et al. 2011; Ordonez and Svenning 2015)."
    ),
    (
        "The theoretical foundation underlying this historical hypothesis operates through dual evolutionary and biogeographical mechanisms. "
        "In climatically stable regions, buffered from the catastrophic environmental extremes of Quaternary glaciation and megadroughts, species "
        "extinction rates are thought to have been substantially attenuated, permitting the persistent survival of ancient, narrow-ranged relictual "
        "taxa ('museum hypothesis') (Fjeldså and Lovett 1997; Magneville et al. 2024). Simultaneously, uninterrupted biological persistence over "
        "millennial timescales provides prolonged ecological opportunities for uninterrupted speciation, ecological specialization, and clade "
        "diversification ('cradle hypothesis') (Stebbins 1974; Blonder et al. 2018). In contrast, regions subjected to violent Quaternary climate "
        "fluctuations—most notably high-latitude and non-topographically sheltered continental interiors—suffered widespread extirpation of endemic "
        "biotas, leaving impoverished modern communities dominated by widespread generalists endowed with superior post-glacial vagility and dispersal "
        "velocity (Sandel et al. 2011; Ordonez and Svenning 2016). Quantifying this historical imprint gained immense traction following the "
        "formulation of post-glacial climate velocity (Loarie et al. 2009; Sandel et al. 2011), which models the minimum horizontal speed a species "
        "must migrate across a topographic surface to continuously track its shifting bioclimatic thermal envelope."
    ),
    (
        "Despite substantial empirical exploration, contemporary literature remains characterized by deep contradictions, empirical discrepancies, "
        "and methodological fractures regarding the magnitude, generality, and causal necessity of historical climate stability. In a landmark global "
        "analysis, Sandel et al. (2011) demonstrated that low post-glacial temperature velocity was strongly associated with high weighted endemism "
        "across global amphibians, birds, and mammals, concluding that Quaternary stability is a preeminent determinant of terrestrial endemism. "
        "Similarly, Feng et al. (2016) reported that palaeoclimate stability governed threatened plant endemism across China, and Acevedo and Sandel "
        "(2021) identified historical stability as a vital predictor of avian diversity. However, an emerging counter-body of research suggests that "
        "the apparent explanatory power of palaeoclimate stability diminishes sharply once contemporary climate and spatial structures are rigorously "
        "modeled. In Chinese woody plants, Xu et al. (2019) observed that palaeoclimate accounted for only 1.1% of species richness variance once "
        "modern climate was absorbed, though it exerted a stronger influence on phylogenetic relatedness. In a high-resolution biome modeling study "
        "spanning 2,605 continuous time slices across Africa, Scheiter et al. (2026) revealed surprisingly low spatial congruence between stable "
        "Quaternary biomes and modern species richness hotspots, suggesting that stability is neither necessary nor sufficient for diversity maintenance. "
        "Furthermore, Fastovich et al. (2020) demonstrated across 13 alternative palaeoclimate estimates that the sign, magnitude, and statistical "
        "significance of biodiversity-stability relationships varied dramatically depending on the general circulation model (GCM) selected."
    ),
    (
        "A critical synthesis of published research reveals three profound methodological vulnerabilities that have systematically hindered robust "
        "inference in macroecological stability studies. First is the ubiquitous presence of spatial autocorrelation (Moran's I = 0.20 to 0.40). "
        "Because adjacent grid cells share physical continuity, evolutionary histories, and climatic regimes, standard ordinary least squares (OLS) "
        "and unpenalized non-spatial regressions suffer from severely inflated nominal degrees of freedom, yielding artificially narrow confidence "
        "intervals and spurious statistical significance (Legendre and Legendre 2012; Roberts et al. 2017). Although spatial autoregressive error "
        "models have been deployed in regional studies (Rakotoarimivo et al. 2013; Oliveira et al. 2020; Xu et al. 2023), machine learning approaches "
        "frequently overlook spatial dependence, evaluating cross-validation folds that allow geographic leakage across nearby test borders."
    ),
    (
        "Second is the unresolved issue of latitudinal and topographic multicollinearity. Long-term Quaternary stability is inherently collinear with "
        "absolute latitude (r = +0.70) and topographic relief (r = -0.26). In the tropics, thermal oscillations between the LGM and present were "
        "substantially smaller than at high latitudes, while steep montane topography offers short elevational corridors that dramatically reduce "
        "horizontal climate velocity (Ashcroft et al. 2012). When non-linear machine learning ensembles (e.g., Random Forest or Gradient Boosting) "
        "are trained on raw, correlated predictors, they aggressively exploit stability features as latent proxies for fine-scale geographic coordinates "
        "and terrain heterogeneity, generating deceptively inflated 'feature importance' metrics that masquerade as historical signals (Ploton et al. 2020)."
    ),
    (
        "Third, virtually all previous investigations rely upon mean-regression frameworks (OLS or conditional expectations) that implicitly assume "
        "symmetric, normally distributed Gaussian errors. However, ecological limiting-factor theory asserts that contemporary energy and moisture "
        "establish an upper potential ceiling on species richness, while historical disturbances, local extinctions, and dispersal limitations "
        "prevent assemblages from achieving this theoretical optimum (Kumbhakar and Lovell 2000; Cade and Noon 2003). Standard mean regressions "
        "fail to detect upper-bound constraints and cannot distinguish between structural ecological shortfall and stochastic observational noise. "
        "Finally, existing studies remain taxonomically fragmented, evaluating plants, mammals, or birds in isolated models without unified statistical "
        "hypothesis testing of inter-taxa slope equality (Wang et al. 2020; Huang et al. 2023; Magneville et al. 2024)."
    ),
    (
        "To rigorously address these unresolved challenges, this study establishes a comprehensive macroecological and machine-learning verification "
        "pipeline across global terrestrial vertebrates. We investigate the central scientific question: Does Quaternary climate stability provide "
        "unique, non-redundant predictive and mechanistic explanatory power for contemporary terrestrial vertebrate richness beyond modern geographic, "
        "bioclimatic, and topographic controls, and how does this relationship vary across taxonomic lineages and macroecological frontiers? "
        "Our specific research objectives are fourfold: (1) to quantify the unique incremental predictive value (Delta R^2) of Quaternary stability "
        "across linear and non-linear machine learning architectures while purging latitudinal and topographic collinearity through training-only "
        "orthogonalization; (2) to eliminate spatial dependency artifacts and spatial cross-validation border leakage via Spatial Eigenvector "
        "Mapping (MEM) and a strict 1,000 km buffered spatial cross-validation framework; (3) to test whether Quaternary climate velocity governs "
        "the macroecological richness ceiling using maximum-likelihood Stochastic Frontier Analysis (SFA); and (4) to evaluate taxonomic slope "
        "heterogeneity across Amphibia, Mammalia, and Reptilia within a unified hierarchical mixed-effects model. By resolving these methodological "
        "vulnerabilities, this research provides a transparent, reproducible, and defensible synthesis of the palaeoclimate stability paradigm."
    )
]

# -----------------------------------------------------------------------------
# 2. STUDY AREA (Target: 350 - 400 words)
# -----------------------------------------------------------------------------
STUDY_AREA_PARAGRAPHS = [
    (
        "The analytical domain of this investigation encompasses all global terrestrial landmasses, spanning approximately 134 million km^2 "
        "across six habitable continents: Africa, Eurasia (analyzed across distinct biogeographical realms as Europe and Asia), North America, "
        "South America, and Oceania. Antarctica, Greenland, and high-arctic permanent ice caps were excluded a priori due to the absence of "
        "permanent terrestrial vertebrate communities and unconstrained paleoclimatic velocity estimations over continental ice sheets. "
        "To ensure multiscale methodological robustness, the global land surface was partitioned into two standardized equal-area spherical "
        "discrete global grids: a primary macro-grid at 5° x 5° spatial resolution (~550 km x 550 km at the equator, N = 755 complete continental "
        "land cells) and a fine-grain macroecological grid at 2° x 2° spatial resolution (~220 km x 220 km at the equator, N = 4,395 complete land cells). "
        "Cells with terrestrial land surface fractions below 0.10 (e.g., extremely isolated oceanic atolls and sub-grid islets) were excluded to prevent "
        "species-area distortion artifacts."
    ),
    (
        "The global study area captures the full spectrum of Earth's terrestrial macroclimates, topographic configurations, and historical glacial "
        "disturbances (Figure 1). It traverses latitudinal extremes from tropical rainforests (Amazon Basin, Congo Basin, Southeast Asian archipelago) "
        "exhibiting exceptional Quaternary climatic persistence and high topographic complexity, through hyper-arid subtropical deserts (Sahara, Arabian "
        "Peninsula, Australian interior) where precipitation stability acts as a severe limiting filter, to temperate deciduous woodlands and high-latitude "
        "boreal and tundra biomes across North America and northern Eurasia that experienced complete glacial obliteration during the LGM (~21 ka). "
        "In accordance with standard macroecological protocols for terrestrial assemblages, the polar bear (Ursus maritimus) was explicitly removed "
        "from mammalian richness aggregations due to its obligate marine sea-ice ecology and reliance on marine trophic webs, which decouples its "
        "geographic occurrence from terrestrial macroclimatic stability surfaces."
    )
]

print("report_text.py updated successfully.")
