import pandas as pd
import streamlit as st
import yfinance as yf
from datetime import timedelta
import math

st.set_page_config(layout="wide")

@st.cache_data
def carregar_tickers_acoes():
    base_tickers = pd.read_csv("IBOV.csv", sep=";")
    tickers = [item + ".SA" for item in base_tickers['Código']]
    return tickers

@st.cache_data
def carregar_graham(empresas):
    dados_graham = {}

    for empresa in empresas:
        try:
            acao = yf.Ticker(empresa)
            dados_historicos = acao.history(period='1d', start='2000-01-01')
            info = acao.info

            eps = info.get('trailingEps', 0)
            bv = info.get('bookValue', 0)

            if isinstance(eps, (int, float)) and isinstance(bv, (int, float)) and eps > 0 and bv > 0:
                graham = math.sqrt(22.5 * eps * bv)

                if not dados_historicos.empty:
                    dados_historicos = dados_historicos.copy()
                    dados_historicos["Graham"] = graham

                    if "Close" in dados_historicos.columns:
                        dados_graham[empresa] = dados_historicos[["Close", "Graham"]]

        except Exception as e:
            st.warning(f"Erro ao processar {empresa}: {e}")

    return dados_graham

@st.cache_data
def carregar_pl(empresas):
    resultados = {}
    
    for empresa in empresas:
        try:
            # Cria o objeto de ação
            dados_acao = yf.Ticker(empresa)
            
            # Tenta acessar as informações da ação
            info_acao = dados_acao.info
            if info_acao is None:
                st.warning(f"Informações não encontradas para a ação {empresa}.")
                resultados[empresa] = None
                continue  # Pula para a próxima ação

            # Verificar se o EPS está disponível
            eps = info_acao.get("trailingEps", None)
            if eps is None:
                st.warning(f"EPS não disponível para a ação {empresa}.")
                resultados[empresa] = None
                continue

            # Tenta obter a cotação mais recente
            cotacao_acao = dados_acao.history(period="1mo")
            if cotacao_acao.empty:
                #st.warning(f"Sem dados de cotação para a ação {empresa}.")
                cotacao_acao = None
            else:
                cotacao_acao = cotacao_acao["Close"].iloc[-1]  # Último preço de fechamento

            # Calcular o P/L (Preço/Lucro), se os dados existirem
            pl_ratio = cotacao_acao / eps if cotacao_acao and eps else None
            resultados[empresa] = pl_ratio

        except Exception as e:
            # Se ocorrer qualquer erro, exibe uma mensagem no Streamlit
            st.error(f"Erro ao acessar os dados da ação {empresa}: {e}")
            resultados[empresa] = None  # Retorna None se ocorrer algum erro

    return resultados  # Retorna um dicionário com o P/L ou None para cada ação 

@st.cache_data
def carregar_dy(empresas):
    resultados = {}
    for empresa in empresas:
        acao = yf.Ticker(empresa)
        dados = acao.info

        dividend_rate = dados.get('dividendRate', 0)
        current_price = dados.get('currentPrice', 0)

        if current_price > 0:
            dividend_yield = (dividend_rate / current_price) * 100
        else:
            dividend_yield = None

        resultados[empresa] = dividend_yield  # Salva os resultados por empresa

    return resultados  # Retorna um dicionário com os dividend yields

@st.cache_data
def carregar_ebitda(empresas):
    resultado = {}

    for empresa in empresas:
        acao = yf.Ticker(empresa)
        dados = acao.info

        total_revenue = dados.get('totalRevenue')
        ebitda_margins = dados.get('ebitdaMargins')

        print(f"{empresa} -> Receita Total: {total_revenue}, Margem EBITDA: {ebitda_margins}")  # Debug

        if total_revenue and ebitda_margins:
            ebitda = (total_revenue / 100) * ebitda_margins  # Ajuste se necessário
        else:
            ebitda = None

        resultado[empresa] = {
            "EBITDA": ebitda,
            "Margem EBITDA": ebitda_margins
        }

    return resultado

@st.cache_data
def carregar_pvp(empresas):
    resultado={}

    for empresa in empresas:
        acao = yf.Ticker(empresa)
        dados = acao.info

        valor_acao = dados.get('regularMarketPrice')
        valor_patrimonial = dados.get('bookValue')

        if valor_acao and valor_patrimonial:
            p_vp = valor_acao / valor_patrimonial
        else:
            p_vp = None
        
        resultado[empresa]= p_vp 
    return resultado   

lista_acoes = carregar_tickers_acoes()
dados_preco = carregar_graham(lista_acoes)
dados_pl = carregar_pl(lista_acoes)
dados_dy = carregar_dy(lista_acoes)
dados_ebitda = carregar_ebitda(lista_acoes)
dados_pvp = carregar_pvp(lista_acoes)

st.sidebar.header("Filtros")

# 🔹 Substituído multiselect por selectbox para escolher apenas uma ação
acao_selecionada = st.sidebar.selectbox("Escolha uma ação para visualizar", list(dados_preco.keys()))

# 🔹 Filtrar os dados para apenas a ação selecionada
dados_filtrados = {acao_selecionada: dados_preco[acao_selecionada]}

# 🔹 Renomear a coluna Close para "Preço Fechamento"
dados_filtrados[acao_selecionada] = dados_filtrados[acao_selecionada].rename(columns={"Close": "Preço Fechamento", "Graham":"Valor Intrinseco"})


# 🔹 Filtrar datas
data_inicial = dados_filtrados[acao_selecionada].index.min().to_pydatetime()
data_final = dados_filtrados[acao_selecionada].index.max().to_pydatetime()

intervalo_data = st.sidebar.slider(
    "Selecione o período", 
    min_value=data_inicial, 
    max_value=data_final, 
    value=(data_final, data_final), 
    step=timedelta(days=1)
)

dados_preco_filtrado = dados_filtrados[acao_selecionada][
    (dados_filtrados[acao_selecionada].index >= intervalo_data[0]) & 
    (dados_filtrados[acao_selecionada].index <= intervalo_data[1])
]

st.write("""
# Indicadores Fundamentalistas
###### Indicadores fundamentalistas são métricas utilizadas para avaliar a saúde financeira e o valor de uma empresa. Eles ajudam a identificar boas oportunidades de investimento ao analisar seus fundamentos e desempenho econômico.         
""")
st.write("""
## Valor da ação vs Valor Intrínseco
###### A comparação entre o preço de uma ação e seu valor intrínseco, conforme Benjamin Graham, ajuda a identificar se a ação está subvalorizada ou supervalorizada.
""")

# 🔹 Exibir gráfico apenas se houver dados no período selecionado

if not dados_preco_filtrado.empty:
    st.button("ℹ️", help=" Quando o preço de mercado é inferior ao valor intrínseco, pode ser uma boa oportunidade de compra; se for superior, o risco de supervalorização aumenta.")
    st.write(f"### {acao_selecionada}")  
    col1, = st.columns(1)
    col1.line_chart(dados_preco_filtrado[["Preço Fechamento", "Valor Intrinseco"]])
else:
    st.warning("Nenhum dado disponível no intervalo selecionado.")

col2, col3, col4, col5 = st.columns(4) 

 # 🔹 Exibir o P/L no card na col2
pl_acao = dados_pl.get(acao_selecionada, None)
if pl_acao is not None:
    if pl_acao < 10:
            texto_acao = f":green[{pl_acao:.2f}]"
    elif 10 <= pl_acao <=20:
            texto_acao = f":orange[{pl_acao:.2f}]"
    else:
            texto_acao = f":red[{pl_acao:.2f}]"
else:
        texto_acao = "P/L (Preço/Lucro): N/A"
with col2:
    st.button("ℹ️", help="(P/L < 10) → Subvalorizada | (10 ≤ P/L ≤ 20) → Moderada | (P/L > 20) → Supervalorizada")
    st.write(f"""
    ##### P/L (Preço/Lucro)
    #### {texto_acao}
    """)

     # 🔹 Exibir o dy no card na col3
dy_acao = dados_dy.get(acao_selecionada, None)
if dy_acao is not None:
    if dy_acao >5:
            dy_texto = f":green[{dy_acao:.2f}%]"
    elif 2 <= dy_acao <5:
            dy_texto = f":orange[{dy_acao:.2f}%]"
    else:
            dy_texto = f":red[{dy_acao:.2f}%]"
else:
        dy_texto = "DY (Dividend Yield): N/A"
with col3:
    st.button("ℹ️", help="(DY > 5%) → Alto rendimento | (2% ≤ DY ≤ 5%) → Moderado | (DY < 2%) → Baixo rendimento")
    st.write(f"""
    ##### DY (Dividend Yield)
    #### {dy_texto}
    """)  


 # 🔹 Exibir o dy no card na col3
# Exibindo o valor do EBITDA
ebitda_acao = dados_ebitda.get(acao_selecionada, None)
if ebitda_acao is not None:
    ebitda_valor = ebitda_acao.get("EBITDA")  # Obtém o valor do EBITDA
    if isinstance(ebitda_valor, (int, float)):  # Verifica se é número
        if ebitda_valor > 0:
            ebitda_texto = f":green[R$ {ebitda_valor:,.2f}]"  
        else:
            ebitda_texto = f":red[R$ {ebitda_valor:,.2f}]"  
    else:
        ebitda_texto = "EBITDA: N/A"
else:
    ebitda_texto = "EBITDA: N/A"

with col4:
    st.button("ℹ️", help="EBITDA: Verde (> 0) = Positivo | Vermelho (≤ 0) = Negativo\n"
                     "Margem EBITDA: Verde (>30%) = Alta | Laranja (10% a 30%) = Moderada | Vermelho (<10%) = Baixa")
    st.write(f"""
    ##### EBITDA
    #### {ebitda_texto}
    """)

# Exibindo a Margem EBITDA
m_ebitda_texto = "N/A"
ebitda_acao = dados_ebitda.get(acao_selecionada, None)

if ebitda_acao is not None:
    m_ebitda_valor = ebitda_acao.get("Margem EBITDA")  # Obtém o valor da margem EBITDA
    if isinstance(m_ebitda_valor, (int, float)):  # Verifica se é número
        m_ebitda_valor *= 100
        if m_ebitda_valor > 30:
            m_ebitda_texto = f":green[{m_ebitda_valor:,.2f}%]" 
        elif 10 <= m_ebitda_valor < 30:     
            m_ebitda_texto = f":orange[{m_ebitda_valor:,.2f}%]"
        else:
            m_ebitda_texto = f":red[{m_ebitda_valor:,.2f}%]"  # Corrigido aqui, trocando m_ebitda_valor por m_ebitda_texto
    else:
        m_ebitda_texto = "EBITDA: N/A"
else:
    m_ebitda_texto = "EBITDA: N/A"

with col4:
    st.write(f"""
    ##### Margem EBITDA
    #### {m_ebitda_texto}
    """)

 # 🔹 Exibir o dy no card na col3
pvp_acao = dados_pvp.get(acao_selecionada, None)
if pvp_acao is not None:
    if pvp_acao <1:
            pvp_texto = f":green[{pvp_acao:.2f}]"
    elif 1 < pvp_acao <=2:
            pvp_texto = f":orange[{pvp_acao:.2f}]"
    else:
            pvp_texto = f":red[{pvp_acao:.2f}]"
else:
        pvp_texto = "P/VP (Preço sobre Valor Patrimonial): N/A"
with col5:
    st.button("ℹ️", help="(P/VP < 1) → Subvalorizada | (1 ≤ P/VP ≤ 2) → Moderada | (P/VP > 2) → Supervalorizada")
    st.write(f"""
    ##### P/VP (Preço sobre Valor Patrimonial)
    #### {pvp_texto}
    """)
