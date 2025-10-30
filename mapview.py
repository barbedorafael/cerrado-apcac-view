# -*- coding: utf-8 -*-
import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import sqlite3
import pandas as pd
import plotly.express as px
from xml.etree import ElementTree as ET

# Configuração da página
st.set_page_config(
    page_title="APCAC - Cerrado",
    page_icon="🌳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título principal
st.title("🌳 Áreas Prioritárias para Conservação de Águas do Cerrado")
st.markdown("---")

@st.cache_data
def get_available_layers():
    """Lista as camadas APCAC disponíveis"""
    try:
        gpkg_path = "data/apcac/apcac.gpkg"
        conn = sqlite3.connect(gpkg_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'apcac_%' AND name NOT LIKE '%_bho5k';")
        apcac_tables = [table[0] for table in cursor.fetchall()]
        conn.close()

        return apcac_tables
    except Exception as e:
        st.error(f"Erro ao listar camadas: {str(e)}")
        return []

@st.cache_data
def load_apcac_statistics():
    """Carrega as estatísticas pré-computadas do arquivo CSV"""
    try:
        csv_path = "data/apcac/apcac.csv"
        df = pd.read_csv(csv_path, sep=';')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar estatísticas: {str(e)}")
        return None

@st.cache_data
def parse_qml_style():
    """Extrai as configurações de estilo do arquivo QML"""
    try:
        qml_path = "data/apcac/apcac.qml"
        tree = ET.parse(qml_path)
        root = tree.getroot()

        style_map = {}

        # Extrair regras e cores do QML
        rules = root.findall(".//rule")
        symbols = root.findall(".//symbol")

        for rule in rules:
            filter_attr = rule.get('filter', '')
            label = rule.get('label', '')
            symbol_name = rule.get('symbol', '')

            # Extrair código APCAC do filtro
            if 'cd_apcac' in filter_attr:
                code = filter_attr.split("'")[1] if "'" in filter_attr else ''
                if code:
                    style_map[code] = {
                        'label': label,
                        'symbol': symbol_name
                    }

        # Extrair cores dos símbolos
        color_map = {}
        for symbol in symbols:
            symbol_name = symbol.get('name', '')
            color_elem = symbol.find(".//Option[@name='color']")
            if color_elem is not None:
                color_value = color_elem.get('value', '')
                if color_value:
                    # Converter de formato QGIS (R,G,B,A) para hex
                    try:
                        rgba = [int(x) for x in color_value.split(',')]
                        hex_color = f"#{rgba[0]:02x}{rgba[1]:02x}{rgba[2]:02x}"
                        color_map[symbol_name] = hex_color
                    except:
                        color_map[symbol_name] = '#808080'  # Cor padrão

        # Combinar estilos e cores
        for code in style_map:
            symbol_num = style_map[code]['symbol']
            if symbol_num in color_map:
                style_map[code]['color'] = color_map[symbol_num]
            else:
                style_map[code]['color'] = '#808080'

        return style_map

    except Exception as e:
        st.error(f"Erro ao carregar estilos QML: {str(e)}")
        return {}

@st.cache_data
def load_specific_layer(layer_name):
    """Carrega uma camada específica do GPKG"""
    try:
        gpkg_path = "data/apcac/apcac.gpkg"
        gdf = gpd.read_file(gpkg_path, layer=layer_name)
        return gdf
    except Exception as e:
        st.error(f"Erro ao carregar camada {layer_name}: {str(e)}")
        return None

def simplify_geodataframe(gdf, tolerance=0.001):
    """Simplifica as geometrias do GeoDataFrame para melhor performance"""
    if gdf is not None and not gdf.empty:
        # Simplificar geometrias com tolerância baixa (mais detalhada)
        gdf_simplified = gdf.copy()
        gdf_simplified['geometry'] = gdf_simplified['geometry'].simplify(tolerance=tolerance, preserve_topology=True)
        return gdf_simplified
    return gdf

def create_folium_map(gdf_simplified, style_map):
    """Cria o mapa Folium com os dados APCAC otimizado para performance"""

    # Calcular centro do mapa baseado nos dados
    bounds = gdf_simplified.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    # Criar mapa base
    m = folium.Map(
        location=[center_lat, center_lon],
        # zoom_start=7,
        tiles=None,
        prefer_canvas=True  # Melhor performance para muitos elementos
    )

    # Adicionar camadas base
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}',
        attr='Esri National Geographic',
        name='National Geographic',
        overlay=False,
        control=True
    ).add_to(m)

    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        attr='Esri Standard',
        name='Street Map',
        overlay=False,
        control=True
    ).add_to(m)

    # Adicionar dados APCAC se disponíveis
    apcac_col = 'cd_apcac'

    # Criar função de estilo otimizada
    def style_function(feature):
        apcac_code = feature['properties'].get(apcac_col, '')
        color = style_map[apcac_code]['color']

        return {
            'fillColor': color,
            'color': '#333333',
            'weight': 0.3,  # Linha mais fina para melhor performance
            'fillOpacity': 0.6,
            'opacity': 0.8
        }
    
    # Limitar campos no tooltip para melhor performance
    tooltip_fields = [apcac_col, 'nuareacont', 't', 'slope']
    tooltip_aliases = ['APCAC:', 'Área (km²)', 'Elevação média (m)', 'Declividade média (%)']

    # Adicionar camada APCAC com configurações otimizadas
    geojson_layer = folium.GeoJson(
        gdf_simplified.to_json(),
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=[apcac_col],
            aliases=['APCAC: '],
            sticky=False,
            labels=True
        ),
        popup=folium.GeoJsonPopup(
            fields=tooltip_fields,
            aliases=tooltip_aliases
        ),
        name='APCAC',
        smooth_factor=1.0
        )

    geojson_layer.add_to(m)

    # Ajustar zoom para mostrar todos os dados
    if hasattr(gdf_simplified, 'total_bounds'):
        bounds = gdf_simplified.total_bounds
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    # Adicionar controle de camadas
    folium.LayerControl().add_to(m)

    return m

def create_legend(style_map):
    """Cria uma legenda para os códigos APCAC"""

    st.sidebar.markdown("### 📊 Legenda APCAC")

    if style_map:
        # Organizar por categorias
        categories = {
            'Natural - Alto Risco': [],
            'Natural - Sem Risco': [],
            'Antrópica - Alto Risco': [],
            'Antrópica - Sem Risco': []
        }

        for code, info in style_map.items():
            label = info['label']
            color = info['color']

            if 'Predominância natural' in label and 'alto risco' in label:
                categories['Natural - Alto Risco'].append((code, label, color))
            elif 'Predominância natural' in label:
                categories['Natural - Sem Risco'].append((code, label, color))
            elif 'Predominância antrópica' in label and 'alto risco' in label:
                categories['Antrópica - Alto Risco'].append((code, label, color))
            elif 'Predominância antrópica' in label:
                categories['Antrópica - Sem Risco'].append((code, label, color))

        for category, items in categories.items():
            if items:
                st.sidebar.markdown(f"**{category}:**")
                for code, label, color in items:
                    # Criar uma pequena caixa colorida
                    st.sidebar.markdown(
                        f'<div style="display: flex; align-items: center; margin: 2px 0;">'
                        f'<div style="width: 15px; height: 15px; background-color: {color}; '
                        f'border: 1px solid #000; margin-right: 8px;"></div>'
                        f'<span style="font-size: 11px;"><b>{code}</b>: {label.split(" - ")[1] if " - " in label else label}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                st.sidebar.markdown("")
    else:
        st.sidebar.markdown("Legenda não disponível")

def create_statistics_charts(df_stats, style_map):
    """Cria gráficos de barras com as estatísticas APCAC"""

    if df_stats is None or df_stats.empty:
        st.warning("Dados de estatísticas não disponíveis")
        return

    # Preparar dados para gráfico
    df_chart = df_stats.copy()

    # Adicionar cores baseadas no style_map
    colors = []
    for code in df_chart['cd_apcac']:
        if code in style_map:
            colors.append(style_map[code]['color'])
        else:
            colors.append('#808080')

    df_chart['color'] = colors

    # Criar tabs para diferentes visualizações
    tab1, tab2, tab3, tab4 = st.tabs(["Área Bioma", "% Bioma", "Área ZHI", "% ZHI"])

    with tab1:
        st.markdown("**Área no Bioma Cerrado (km²)**")
        fig1 = px.bar(
            df_chart,
            x='cd_apcac',
            y='bio_area_km2',
            color='cd_apcac',
            color_discrete_map={row['cd_apcac']: row['color'] for _, row in df_chart.iterrows()},
            title="Área das Classes APCAC no Bioma Cerrado"
        )
        fig1.update_layout(
            showlegend=False,
            xaxis_title="Classe APCAC",
            yaxis_title="Área (km²)",
            height=400,
            xaxis={'categoryorder': 'total descending'}
        )
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.markdown("**Porcentagem no Bioma Cerrado (%)**")
        fig2 = px.bar(
            df_chart,
            x='cd_apcac',
            y='bio_area_km2_p',
            color='cd_apcac',
            color_discrete_map={row['cd_apcac']: row['color'] for _, row in df_chart.iterrows()},
            title="Porcentagem das Classes APCAC no Bioma Cerrado"
        )
        fig2.update_layout(
            showlegend=False,
            xaxis_title="Classe APCAC",
            yaxis_title="Porcentagem (%)",
            height=400,
            xaxis={'categoryorder': 'total descending'}
        )
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.markdown("**Área na Zona de Influência Hidrológica (km²)**")
        fig3 = px.bar(
            df_chart,
            x='cd_apcac',
            y='zhi_area_km2',
            color='cd_apcac',
            color_discrete_map={row['cd_apcac']: row['color'] for _, row in df_chart.iterrows()},
            title="Área das Classes APCAC na Zona de Influência Hidrológica"
        )
        fig3.update_layout(
            showlegend=False,
            xaxis_title="Classe APCAC",
            yaxis_title="Área (km²)",
            height=400,
            xaxis={'categoryorder': 'total descending'}
        )
        st.plotly_chart(fig3, use_container_width=True)

    with tab4:
        st.markdown("**Porcentagem na Zona de Influência Hidrológica (%)**")
        fig4 = px.bar(
            df_chart,
            x='cd_apcac',
            y='zhi_area_km2_p',
            color='cd_apcac',
            color_discrete_map={row['cd_apcac']: row['color'] for _, row in df_chart.iterrows()},
            title="Porcentagem das Classes APCAC na Zona de Influência Hidrológica"
        )
        fig4.update_layout(
            showlegend=False,
            xaxis_title="Classe APCAC",
            yaxis_title="Porcentagem (%)",
            height=400,
            xaxis={'categoryorder': 'total descending'}
        )
        st.plotly_chart(fig4, use_container_width=True)

@st.cache_resource(show_spinner=False)
def build_cached_map(layer_name: str, style_map: dict, tolerance=0.001):
    """Cria e cacheia o mapa Folium para uma camada específica"""
    gdf = load_specific_layer(layer_name)
    gdf_simplified = simplify_geodataframe(gdf, tolerance)
    return create_folium_map(gdf_simplified, style_map)

def main():
    """Função principal do dashboard"""

    # Sidebar com informações e controles
    st.sidebar.markdown("### ℹ️ Informações do Projeto")
    st.sidebar.markdown("""
    Este dashboard apresenta as **Áreas Prioritárias para Conservação de Águas do Cerrado (APCAC)**.

    As áreas são classificadas considerando:
    - **Predominância**: Natural ou Antrópica
    - **Importância Hidrológica**: Extremamente Alta, Muito Alta, Alta, Regular
    - **Nível de Risco**: Alto Risco ou Sem Risco Específico
    """)

    # Carregar dados
    available_layers = get_available_layers()
    style_map = parse_qml_style()
    df_stats = load_apcac_statistics()

    # Controles na sidebar
    st.sidebar.markdown("### 🗂️ Configurações")

    # Seleção de camada
    if available_layers:
        # Determinar índice padrão (preferir nunivotto3)
        default_index = 0
        if 'apcac_nunivotto3' in available_layers:
            default_index = available_layers.index('apcac_nunivotto3')
        elif 'apcac_nunivotto4' in available_layers:
            default_index = available_layers.index('apcac_nunivotto4')
        elif 'apcac_nunivotto5' in available_layers:
            default_index = available_layers.index('apcac_nunivotto5')

        selected_layer = st.sidebar.selectbox(
            "Selecione uma camada:",
            available_layers,
            index=default_index,
            help="Diferentes resoluções de análise das bacias hidrográficas"
        )
    else:
        st.error("Nenhuma camada APCAC encontrada")

    # Criar legenda
    create_legend(style_map)

    # Layout principal
    # Criar e exibir mapa
    with st.spinner('🗺️ Carregando mapa...'):
        m = build_cached_map(selected_layer, style_map)

    # Exibir mapa
    st_folium(
        m,
        width=1400,
        height=700,
        returned_objects=[]
    )



    # Seção de estatísticas completas
    st.markdown("---")
    st.markdown("### 📈 Estatísticas Detalhadas")

    if df_stats is not None:
        create_statistics_charts(df_stats, style_map)
    else:
        st.warning("Estatísticas pré-computadas não disponíveis")

    # Rodapé com informações adicionais
    st.markdown("---")
    st.markdown("""
    ### 📋 Sobre o APCAC

    O sistema APCAC (Áreas Prioritárias para Conservação de Águas do Cerrado) foi desenvolvido para identificar
    e priorizar áreas críticas para a conservação dos recursos hídricos no bioma Cerrado.

    **Fonte dos dados:** Projeto de pesquisa sobre conservação de águas do Cerrado
    """)

if __name__ == "__main__":
    main()