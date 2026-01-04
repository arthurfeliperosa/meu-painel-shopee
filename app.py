import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dashboard ROI - Shopee & Meta", page_icon="🚀", layout="wide")

# --- CSS CLEAN ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: #1f2937; border: 1px solid #374151;
        padding: 15px; border-radius: 10px;
    }
    div[data-testid="stMetricLabel"] { color: #9ca3af; font-size: 14px; }
    div[data-testid="stMetricValue"] { color: #f3f4f6; font-size: 26px; }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 Analisador de Lucro: Shopee vs Ads")
st.markdown("---")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("📂 Importar Dados")
    shopee_file = st.file_uploader("Relatório Shopee", type=["csv", "xlsx"])
    meta_file = st.file_uploader("Relatório Meta Ads", type=["csv", "xlsx"])

# --- FUNÇÕES DE SEGURANÇA ---

def encontrar_inicio_tabela(arquivo_bytes):
    """
    Escaneia as primeiras 20 linhas do arquivo para achar onde começa o cabeçalho real.
    Procura por palavras-chave típicas de colunas.
    """
    try:
        # Decodifica bytes para string para ler linha a linha
        content = arquivo_bytes.getvalue().decode('utf-8', errors='ignore')
        lines = content.split('\n')
        
        keywords = ['order id', 'purchase time', 'data', 'date', 'campaign name', 'ad name', 'day', 'reporting starts']
        
        for i, line in enumerate(lines[:20]): # Olha apenas as primeiras 20 linhas
            line_lower = line.lower()
            # Se encontrar 2 ou mais keywords na mesma linha, é o cabeçalho
            matches = sum(1 for k in keywords if k in line_lower)
            if matches >= 1:
                return i
        return 0 # Se não achar nada especial, assume linha 0
    except:
        return 0

def limpar_moeda(valor):
    if isinstance(valor, (int, float)): return valor
    if pd.isna(valor) or valor == '': return 0.0
    valor = str(valor).lower().replace('r$', '').replace('brl', '').replace('usd', '')
    valor = valor.replace('.', '').replace(',', '.')
    try: return float(valor.strip())
    except: return 0.0

def processar_planilha(file):
    try:
        # 1. Detectar onde começa a tabela
        header_row = encontrar_inicio_tabela(file)
        
        # 2. Ler o arquivo pulando as linhas de "lixo" (metadata)
        file.seek(0) # Voltar ponteiro para o início
        if file.name.endswith('.csv'):
            try:
                df = pd.read_csv(file, header=header_row, on_bad_lines='skip')
            except:
                file.seek(0)
                df = pd.read_csv(file, header=header_row, sep=';', on_bad_lines='skip', encoding='latin1')
        else:
            df = pd.read_excel(file, header=header_row)

        # 3. VERIFICAÇÃO CRÍTICA: O arquivo está vazio?
        if df.empty or len(df) == 0:
            return None, "Arquivo vazio (sem dados)"

        # 4. Normalizar Colunas (Minúsculas e sem espaços extras)
        df.columns = [str(c).strip().lower() for c in df.columns]

        # 5. Identificar Colunas Automaticamente
        col_data = next((c for c in df.columns if any(k in c for k in ['date', 'data', 'time', 'day', 'created_at', 'starts'])), None)
        col_valor = next((c for c in df.columns if any(k in c for k in ['amount', 'spent', 'cost', 'valor', 'total', 'comiss', 'income', 'payab'])), None)

        if not col_data or not col_valor:
            return None, f"Colunas não identificadas. Encontradas: {list(df.columns)}"

        # 6. Processar Dados
        # Remove linhas onde a data é vazia
        df = df.dropna(subset=[col_data])
        
        # Converte Data (Força erros a NaT e remove)
        df['Data_Convertida'] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce').dt.date
        df = df.dropna(subset=['Data_Convertida'])
        
        # Se após limpar datas o df ficar vazio (ex: só tinha cabeçalho), retorna None
        if df.empty:
            return None, "Sem datas válidas"

        # Limpa Valores
        df[col_valor] = df[col_valor].apply(limpar_moeda)
        
        # Agrupa por dia
        return df.groupby('Data_Convertida')[col_valor].sum().reset_index(), "Sucesso"

    except Exception as e:
        return None, str(e)

# --- APP PRINCIPAL ---
if shopee_file and meta_file:
    df_s, status_s = processar_planilha(shopee_file)
    df_m, status_m = processar_planilha(meta_file)

    # Exibir erros se houver, mas de forma amigável
    if df_s is None: st.warning(f"⚠️ Shopee: {status_s}")
    if df_m is None: st.warning(f"⚠️ Meta Ads: {status_m}")

    if df_s is not None and df_m is not None:
        df_s.columns = ['Data', 'Receita']
        df_m.columns = ['Data', 'Custo']
        
        df_final = pd.merge(df_s, df_m, on='Data', how='outer').fillna(0)
        df_final['Saldo'] = df_final['Receita'] - df_final['Custo']
        df_final = df_final.sort_values('Data')

        # Filtro de Data
        min_date, max_date = df_final['Data'].min(), df_final['Data'].max()
        st.sidebar.markdown("---")
        
        # Se houver apenas 1 dia de dados (min == max), não mostra range, mostra só aviso
        if min_date == max_date:
            st.sidebar.info(f"📅 Exibindo dados de: {min_date}")
            df_filtered = df_final
        else:
            r = st.sidebar.date_input("Período", [min_date, max_date], min_value=min_date, max_value=max_date)
            if len(r) == 2:
                df_filtered = df_final[(df_final['Data'] >= r[0]) & (df_final['Data'] <= r[1])]
            else:
                df_filtered = df_final

        # Cards
        c1, c2, c3 = st.columns(3)
        rec = df_filtered['Receita'].sum()
        cus = df_filtered['Custo'].sum()
        luc = df_filtered['Saldo'].sum()
        
        c1.metric("💰 Shopee", f"R$ {rec:,.2f}")
        c2.metric("💸 Meta Ads", f"R$ {cus:,.2f}")
        c3.metric("📈 Lucro", f"R$ {luc:,.2f}", delta=f"{(luc/cus)*100:.1f}% ROI" if cus > 0 else "N/A")

        # Gráfico e Tabela
        fig = px.line(df_filtered, x='Data', y=['Receita', 'Custo', 'Saldo'], markers=True,
                      color_discrete_map={'Receita': '#00C853', 'Custo': '#D50000', 'Saldo': '#2962FF'})
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
        
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df_filtered.style.format("R$ {:.2f}", subset=['Receita', 'Custo', 'Saldo']), use_container_width=True)

else:
    st.info("Aguardando uploads...")
