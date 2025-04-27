# Dashboard DCA ETF

Ce projet fournit un tableau de bord Streamlit pour piloter une stratégie de Dollar-Cost Averaging (DCA) sur un panier d'ETFs.

## Installation

```bash
git clone https://github.com/<votre-utilisateur>/dca-dashboard-etf.git
cd dca-dashboard-etf
python -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate sur Windows
pip install -r requirements.txt
```

## Configuration

Créez un fichier `secrets.toml` dans le dossier `.streamlit/` contenant :

```toml
[FRED]
FRED_API_KEY = "VOTRE_CLE_API_FRED"
```

## Lancement

```bash
streamlit run dca_dashboard/app.py
```

## Structure du projet

```
dca-dashboard-etf/
├── .github/
│   └── workflows/
│       └── ci.yml
├── assets/
│   └── logo.png
├── css/
│   └── styles.css
├── dca_dashboard/
│   ├── __init__.py
│   ├── constants.py
│   ├── data_loader.py
│   ├── scoring.py
│   ├── plotting.py
│   ├── streamlit_utils.py
│   └── app.py
├── tests/
│   ├── test_data_loader.py
│   └── test_scoring.py
├── .gitignore
├── README.md
└── requirements.txt
```

## Tests

```bash
pytest
```