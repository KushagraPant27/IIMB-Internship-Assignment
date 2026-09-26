# config.py
# ---------------------------------------------------------------------------
# List of target incubators/accelerators and their website URLs.
#
# IMPORTANT: These homepage / "About Us" URLs were filled in from general
# knowledge and were NOT individually re-verified against each live site in
# this session (the sandbox this code was written in cannot reach the
# internet). BEFORE running a full 10-year scrape, please:
#   1. Open each "homepage" URL in a browser and confirm it's current.
#   2. Open each "about" URL and confirm it actually is the About Us page
#      (many sites use /about, /about-us, /who-we-are, etc. - these vary a
#      lot and some may have changed over the org's history).
#   3. Delete/replace any organization you don't want scraped.
#
# You do NOT need the URL to have existed in 2017 - the script asks the
# Wayback Machine for the closest available snapshot to each target month,
# so it will simply skip months where no snapshot exists yet.
# ---------------------------------------------------------------------------

ORGANIZATIONS = [
    {
        "name": "NASSCOM 10,000 Startups",
        "homepage": "https://nasscom.in/",
        "about": "https://nasscom.in/about-us",
    },
    {
        "name": "CIIE IIM-A",
        "homepage": "https://www.iima.ac.in/",
        "about": "https://www.iima.ac.in/faculty-research/centers/Centre-for-Innovation-Incubation-Entrepreneurship",
    },
    {
        "name": "T-Hub",
        "homepage": "https://www.t-hub.co/",
        "about": "https://www.t-hub.co/about-us",
    },
    {
        "name": "SINE (Society for Innovation & Entrepreneurship) - IIT Bombay",
        "homepage": "https://www.sineiitb.org/",
        "about": "https://www.sineiitb.org/about-us/",
    },
    {
        "name": "IIT Madras Incubation Cell (IITMIC)",
        "homepage": "http://iitm.ac.in/research-park/incubation-cell",
        "about": "http://iitm.ac.in/research-park/incubation-cell",
    },
    {
        "name": "Foundation For Innovation And Technology Transfer, IIT-D",
        "homepage": "https://fitt-iitd.in/web/home",
        "about": "https://fitt-iitd.in/web/aboutus",
    },
    {
        "name": "Life Science Incubator at IKP Knowledge Park",
        "homepage": "https://ikpknowledgepark.com/life-sciences-incubator/",
        "about": "https://ikpknowledgepark.com/about-us/",
    },
    {
        "name": "NSRCEL, IIM Bangalore",
        "homepage": "https://nsrcel.org/",
        "about": "https://nsrcel.org/about-us/",
    },
    {
        "name": "Kerala Startup Mission KSUM",
        "homepage": "https://startupmission.kerala.gov.in/",
        "about": "https://startupmission.kerala.gov.in/about",
    },
    {
        "name": "Maker Village - Kochi",
        "homepage": "https://makervillage.in/",
        "about": "https://makervillage.in/about-us/",
    },
    {
        "name": "Bio Incubator at C-CAMP",
        "homepage": "https://www.ccamp.res.in/incubation",
        "about": "https://www.ccamp.res.in/about",
    },
    {
        "name": "IIM Calcutta Innovation Park",
        "homepage": "https://iimcip.org/",
        "about": "https://iimcip.org/about-us/about-iimcip/",
    },
    {
        "name": "Venture Center",
        "homepage": "https://www.venturecenter.co.in/",
        "about": "https://www.venturecenter.co.in/about",
    },
    {
        "name": "STEP - IIT Roorkee",
        "homepage": "https://iitr.ac.in/Centres/Centre%20for%20Space%20Science%20and%20Technology/Activities/STEP2025_and_IPSC-2025.html",
        "about": "https://iitr.ac.in/Centres/Centre%20for%20Space%20Science%20and%20Technology/Activities/STEP2025_and_IPSC-2025.html",
    },
    {
        "name": "MITCON Biotechnology Business Incubation Centre",
        "homepage": "https://mitoconbiopharma.com/",
        "about": "https://mitoconbiopharma.com/about-us/",
    },
    {
        "name": "SIDBI Innovation & Incubation Centre, IIT Kanpur",
        "homepage": "https://siicincubator.com/",
        "about": "https://siicincubator.com/who-we-are",
    },
    {
        "name": "IIIT-H Foundation",
        "homepage": "https://cie.iiit.ac.in/",
        "about": "https://cie.iiit.ac.in/about/",
    },
    {
        "name": "Amity Innovation Incubator",
        "homepage": "https://amity.edu/aii/",
        "about": "https://amity.edu/aii/AboutUs.aspx",
    },
    {
        "name": "IKP Eden",
        "homepage": "https://ikpeden.com/",
        "about": "https://ikpeden.com/about-us/",
    },
    {
        "name": "TBI BITS Pilani",
        "homepage": "https://pieds-bitspilani.org/",
        "about": "https://pieds-bitspilani.org/about/",
    },
]

# Date range for monthly snapshots (inclusive), oldest -> newest
START_YEAR = 2017
START_MONTH = 1
END_YEAR = 2026
END_MONTH = 9
