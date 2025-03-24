# app.py
import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import plotly.express as px
import base64

# Configuration de la page
st.set_page_config(page_title="Gestion Financière", layout="wide")

# Menu latéral
st.sidebar.header("Navigation")
page = st.sidebar.selectbox("Choisir une section", 
                           ["Calculateur d'Intérêts", "Portefeuille", "Watchlist", "Informations Financières"])

# Fonction pour calculer les intérêts composés
def calculer_capital(montant, taux, duree, type_invest="Actions"):
    capital = 0
    evolution = []
    for annee in range(1, duree + 1):
        taux_ajuste = taux / 100 * (1.2 if type_invest == "Actions" else 0.8)
        capital = (capital + montant) * (1 + taux_ajuste)
        evolution.append((annee, round(capital, 2)))
    return pd.DataFrame(evolution, columns=["Année", "Capital accumulé"])

# Fonction pour calculer la volatilité et la VaR
def calculer_risque(historique):
    try:
        rendements = historique.pct_change().dropna()
        if len(rendements) < 2:
            return "N/A", "N/A"
        volatilite = rendements.std() * np.sqrt(252)  # Annualisée
        var = np.percentile(rendements, 5)  # VaR à 95%
        return volatilite, var
    except:
        return "N/A", "N/A"

# Fonction pour convertir un dataframe en lien de téléchargement Excel
def to_excel_download_link(df, filename="data.xlsx"):
    towrite = pd.ExcelWriter(filename, engine='xlsxwriter')
    df.to_excel(towrite, index=False, sheet_name='Feuille1')
    towrite.close()
    with open(filename, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">📥 Télécharger en Excel</a>'
    return href

# Fonction pour rechercher un symbole depuis un nom
@st.cache_data
def trouver_symbole(nom_ou_symbole):
    nom_ou_symbole = nom_ou_symbole.strip().upper()
    if len(nom_ou_symbole) <= 5:
        return nom_ou_symbole  # Probablement un symbole
    try:
        recherche = yf.Ticker(nom_ou_symbole)
        if recherche:
            return nom_ou_symbole
    except:
        pass
    return nom_ou_symbole

# Suggestions d'actifs populaires
suggestions = ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN", "VTI", "SPY", "XIC.TO", "QQQ"]

# Section 1 : Calculateur d'Intérêts Composés
if page == "Calculateur d'Intérêts":
    st.title("💰 Calculateur de Placement et Intérêts Composés")

    col1, col2 = st.columns(2)
    with col1:
        montant_annuel = st.number_input("Montant investi par an ($)", min_value=0.0, value=1000.0, step=100.0)
        taux_interet = st.number_input("Taux d'intérêt annuel (%)", min_value=0.0, value=5.0, step=0.1)
    with col2:
        annees = st.number_input("Nombre d'années", min_value=1, value=10, step=1)
        type_invest = st.selectbox("Type d'investissement", ["Actions", "Obligations"])

    if st.button("Calculer"):
        df = calculer_capital(montant_annuel, taux_interet, annees, type_invest)

        st.subheader("📈 Évolution du capital")
        st.dataframe(df.style.format({"Capital accumulé": "${:,.2f}"}))

        fig = px.line(df, x="Année", y="Capital accumulé", title="Croissance du capital")
        st.plotly_chart(fig)

        total = df["Capital accumulé"].iloc[-1]
        st.success(f"Capital final après {annees} ans : ${total:,.2f}")

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Télécharger les données CSV", csv, "evolution_capital.csv", "text/csv")

        st.markdown(to_excel_download_link(df, "evolution_capital.xlsx"), unsafe_allow_html=True)

# Section 2 : Portefeuille
elif page == "Portefeuille":
    st.title("📊 Mon Portefeuille")

    if "portefeuille" not in st.session_state:
        st.session_state.portefeuille = pd.DataFrame(columns=["Actif", "Type", "Quantité", "Prix Achat", "Valeur Actuelle"])

    with st.form(key="ajout_actif"):
        recherche = st.text_input("Nom ou symbole du placement")
        quantite = st.number_input("Quantité", min_value=0.0, step=1.0)
        bouton_ajouter = st.form_submit_button("Ajouter")

        if bouton_ajouter and recherche:
            try:
                symbole_final = recherche.strip().upper()
                actif = yf.Ticker(symbole_final)
                info = actif.info
                hist = actif.history(period="1d")
                if hist.empty:
                    raise ValueError("Aucune donnée disponible")
                prix_actuel = hist["Close"].iloc[-1]
                prix_achat = prix_actuel
                secteur = info.get("sector", "")
                if "ETF" in info.get("quoteType", "").upper() or "ETF" in info.get("longName", "").upper():
                    type_actif = "FNB"
                elif secteur == "Financial Services" or "BOND" in info.get("longName", "").upper():
                    type_actif = "Obligations"
                else:
                    type_actif = "Actions"
                new_row = {"Actif": symbole_final, "Type": type_actif, "Quantité": quantite, "Prix Achat": prix_achat, "Valeur Actuelle": prix_actuel}
                st.session_state.portefeuille = pd.concat([st.session_state.portefeuille, pd.DataFrame([new_row])], ignore_index=True)
                st.success(f"{symbole_final} ajouté au portefeuille !")
            except Exception as e:
                st.error(f"Erreur : {str(e)}")

    if not st.session_state.portefeuille.empty:
        st.subheader("📈 Composition du portefeuille")

        if st.button("🔄 Mettre à jour les données"):
            for i, row in st.session_state.portefeuille.iterrows():
                try:
                    hist = yf.Ticker(row["Actif"]).history(period="1d")
                    if not hist.empty:
                        st.session_state.portefeuille.at[i, "Valeur Actuelle"] = hist["Close"].iloc[-1]
                except:
                    pass

        st.session_state.portefeuille["Valeur Totale"] = st.session_state.portefeuille["Quantité"] * st.session_state.portefeuille["Valeur Actuelle"]
        st.session_state.portefeuille["Profit/Perte"] = (st.session_state.portefeuille["Valeur Actuelle"] - st.session_state.portefeuille["Prix Achat"]) * st.session_state.portefeuille["Quantité"]

        st.metric("💼 Valeur totale du portefeuille", f"${st.session_state.portefeuille['Valeur Totale'].sum():,.2f}")

        st.subheader("📋 Détail des actifs")
        st.dataframe(st.session_state.portefeuille.style.format({
            "Prix Achat": "${:.2f}", "Valeur Actuelle": "${:.2f}",
            "Valeur Totale": "${:,.2f}", "Profit/Perte": "${:,.2f}"
        }))

        repartition = st.session_state.portefeuille.groupby("Type")["Valeur Totale"].sum().reset_index()
        fig = px.pie(repartition, names="Type", values="Valeur Totale", title="Répartition du portefeuille")
        st.plotly_chart(fig)

        st.markdown(to_excel_download_link(st.session_state.portefeuille, "portefeuille.xlsx"), unsafe_allow_html=True)

        # Modification d’un actif existant
        st.subheader("✏️ Modifier un placement existant")
        actif_a_modifier = st.selectbox("Sélectionner un actif à modifier", st.session_state.portefeuille["Actif"].tolist())
        if actif_a_modifier:
            row_index = st.session_state.portefeuille[st.session_state.portefeuille["Actif"] == actif_a_modifier].index[0]
            nouvelle_quantite = st.number_input("Nouvelle quantité", min_value=0.0, value=float(st.session_state.portefeuille.at[row_index, "Quantité"]), step=1.0)
            nouveau_prix = st.number_input("Nouveau prix d'achat", min_value=0.0, value=float(st.session_state.portefeuille.at[row_index, "Prix Achat"]), step=0.1)
            if st.button("Mettre à jour ce placement"):
                st.session_state.portefeuille.at[row_index, "Quantité"] = nouvelle_quantite
                st.session_state.portefeuille.at[row_index, "Prix Achat"] = nouveau_prix
                st.success(f"{actif_a_modifier} mis à jour avec succès.")

        actif_a_supprimer = st.selectbox("🗑️ Supprimer un actif", st.session_state.portefeuille["Actif"].tolist())
        if st.button("Supprimer"):
            st.session_state.portefeuille = st.session_state.portefeuille[st.session_state.portefeuille["Actif"] != actif_a_supprimer]
            st.success(f"{actif_a_supprimer} a été supprimé du portefeuille.")
 # Section 3 : Watchlist
elif page == "Watchlist":
    st.title("👀 Ma Watchlist")

    if "watchlist" not in st.session_state:
        st.session_state.watchlist = []

    symbole = st.text_input("Ajouter un symbole à la watchlist (ex: AAPL)")
    if st.button("Ajouter") and symbole:
        st.session_state.watchlist.append(symbole.upper())
        st.success(f"{symbole.upper()} ajouté à la watchlist !")

    if st.session_state.watchlist:
        st.subheader("Ma Watchlist")
        data = {}
        risques = []
        for symbole in st.session_state.watchlist:
            try:
                actif = yf.Ticker(symbole)
                hist = actif.history(period="1y")
                if hist.empty:
                    raise ValueError("Aucune donnée disponible")
                data[symbole] = hist["Close"].iloc[-1]
                volatilite, var = calculer_risque(hist["Close"])
                risques.append({"Volatilité (annuelle)": volatilite, "VaR (95%)": var})
            except:
                data[symbole] = "N/A"
                risques.append({"Volatilité (annuelle)": "N/A", "VaR (95%)": "N/A"})

        watch_df = pd.DataFrame(list(data.items()), columns=["Symbole", "Prix Actuel"])
        risque_df = pd.DataFrame(risques)
        watch_complet = pd.concat([watch_df, risque_df], axis=1)
        st.dataframe(watch_complet.style.format({
            "Prix Actuel": lambda x: "N/A" if x == "N/A" else "${:.2f}".format(x),
            "Volatilité (annuelle)": lambda x: "N/A" if x == "N/A" else "{:.2%}".format(x),
            "VaR (95%)": lambda x: "N/A" if x == "N/A" else "{:.2%}".format(x)
        }))

        watch_data = pd.DataFrame()
        for symbole in st.session_state.watchlist:
            try:
                hist = yf.Ticker(symbole).history(period="1y")["Close"]
                watch_data[symbole] = hist
            except:
                pass
        if not watch_data.empty:
            st.line_chart(watch_data)

        symbole_suppr = st.selectbox("Supprimer un symbole de la watchlist", st.session_state.watchlist)
        if st.button("Supprimer le symbole"):
            st.session_state.watchlist.remove(symbole_suppr)
            st.success(f"{symbole_suppr} supprimé de la watchlist.")

# Section 4 : Informations Financières
elif page == "Informations Financières":
    st.title("ℹ️ Informations Financières")

    symbole = st.text_input("Entrez un symbole (ex: AAPL)")
    if symbole:
        try:
            actif = yf.Ticker(symbole.upper())
            info = actif.info
            st.subheader(f"{info['longName']} ({symbole.upper()})")

            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Secteur** : {info.get('sector', 'N/A')}")
                st.write(f"**Prix actuel** : ${info.get('currentPrice', 'N/A'):.2f}")
                st.write(f"**Capitalisation** : ${info.get('marketCap', 0):,.0f}")
            with col2:
                st.write(f"**PER** : {info.get('trailingPE', 'N/A'):.2f}")
                st.write(f"**Dividende** : {info.get('dividendYield', 0) * 100:.2f}%")
                st.write(f"**52 semaines** : ${info.get('fiftyTwoWeekLow', 0):.2f} - ${info.get('fiftyTwoWeekHigh', 0):.2f}")

            hist = actif.history(period="1y")
            if not hist.empty:
                volatilite, var = calculer_risque(hist["Close"])
                st.write(f"**Volatilité (annuelle)** : {'N/A' if volatilite == 'N/A' else f'{volatilite:.2%}'}")
                st.write(f"**VaR (95%)** : {'N/A' if var == 'N/A' else f'{var:.2%}'} (perte potentielle max sur 1 jour)")

            periode = st.selectbox("Période", ["1mo", "6mo", "1y", "5y"])
            hist = actif.history(period=periode)
            if not hist.empty:
                st.line_chart(hist["Close"].rename(f"Historique {symbole.upper()} ({periode})"))
        except Exception as e:
            st.error(f"Erreur : {str(e)}")

# Footer
st.sidebar.markdown("---")
st.sidebar.write(f"Date : {datetime.now().strftime('%Y-%m-%d')}")           