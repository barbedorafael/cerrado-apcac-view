# Visualizador APCAC Cerrado

Painel interativo em Streamlit que apresenta as *Áreas Prioritárias para Conservação de Águas do Cerrado* (APCAC). O aplicativo exibe a avaliação geoespacial produzida pelo Instituto Cerrados, combinando camadas vetoriais das APCAC, estatísticas hidrológicas e estilos cartográficos pré-configurados derivados de arquivos QML do QGIS.

## Principais Funcionalidades
- Exibe polígonos das APCAC sobre mapas de base da Esri selecionáveis no Folium.
- Lê camadas e estilos diretamente do geopackage distribuído pelo projeto de pesquisa.
- Mostra na barra lateral uma legenda agrupada por predominância natural/antrópica e nível de risco.
- Apresenta estatísticas precomputadas de área para o bioma Cerrado e para a zona de influência hidrológica em gráficos interativos do Plotly.
- Faz cache de camadas, estilos e mapas para manter a experiência no Streamlit responsiva.

## Estrutura do Repositório
```
.
├── mapview.py          # Ponto de entrada da aplicação Streamlit
├── data/
│   ├── apcac/          # Geopackage das APCAC, estilos (QML) e estatísticas em CSV
│   ├── indexes/        # Índices raster usados no projeto mais amplo
│   ├── variables/      # Variáveis ambientais em raster (pares TIF/QML)
│   └── index.csv       # Catálogo dos ativos disponíveis com metadados
└── docs/
    └── report_A030FP03_cerrados_2025-10-14.pdf  # Relatório do projeto
```

Arquivos raster volumosos são mantidos localmente e não devem ser redistribuídos sem o consentimento do provedor dos dados. Preserve a estrutura de pastas relativa para que o aplicativo encontre os recursos.

## Primeiros Passos
### Pré-requisitos
- Python 3.10 ou superior.
- Pilha Python com suporte geoespacial (GDAL/GEOS/PROJ) exigida pelo GeoPandas. Em sistemas Debian/Ubuntu instale com:
  ```
  sudo apt-get install gdal-bin libgdal-dev
  export CPLUS_INCLUDE_PATH=/usr/include/gdal
  export C_INCLUDE_PATH=/usr/include/gdal
  ```
  Usuários de Windows e macOS devem instalar o GDAL via conda-forge ou pacotes específicos do sistema antes de instalar as dependências Python.
- Opcional, mas recomendado: um ambiente virtual (`venv`, `conda` ou `mamba`).

### Instalar dependências
```bash
python3 -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install streamlit folium streamlit-folium geopandas pandas plotly
```

Se você já gerencia dependências com `conda`, instale `geopandas`, `streamlit`, `folium` e `plotly` pelo canal `conda-forge` para trazer automaticamente as bibliotecas nativas compatíveis.

### Executar a aplicação
```bash
streamlit run mapview.py
```
O Streamlit exibirá uma URL local (ex.: `http://localhost:8501`). Abra no navegador para explorar o mapa e os gráficos.

## Fontes de Dados
O aplicativo espera o conjunto de dados distribuído pelo projeto APCAC:

- `data/apcac/apcac.gpkg`: geopackage principal contendo as diferentes camadas das APCAC (malha BHO 5k e hierarquia de bacias Otto).
- `data/apcac/apcac.csv`: tabela com áreas precomputadas para cada classe APCAC no bioma Cerrado e na zona de influência hidrológica.
- `data/apcac/apcac.qml`: simbologia QGIS utilizada para mapear códigos APCAC para cores e rótulos. Interpretada em tempo de execução para estilizar as camadas do Folium e a legenda no Streamlit.
- `data/index.csv`: catálogo de metadados que descreve todas as camadas e rasters entregues pelo projeto Instituto Cerrados.
- `data/variables/` e `data/indexes/`: grades raster de suporte (variáveis ambientais e índices) mantidas para reprodutibilidade, embora não sejam carregadas diretamente pelo aplicativo.
- `data/LEIAME_006.txt`: documento em português fornecido com o pacote de dados, contendo links e referências bibliográficas.

Siga as orientações do Instituto Cerrados quanto a licenciamento, citação e atualizações. Se mover o diretório `data/`, atualize os caminhos definidos em `mapview.py`.

## Como Funciona
- **Descoberta de camadas:** `get_available_layers()` consulta o catálogo do geopackage em busca de tabelas com prefixo `apcac_`. Novas camadas com o mesmo prefixo são reconhecidas automaticamente.
- **Estilização:** `parse_qml_style()` converte regras XML do QGIS em um dicionário Python que relaciona códigos APCAC com cores em hexadecimal e rótulos descritivos, reutilizados na legenda e nos gráficos.
- **Renderização do mapa:** `build_map()` carrega e simplifica geodados com GeoPandas, envia para o Folium e guarda o resultado em cache para recarregamentos instantâneos quando o usuário altera abas ou configurações.
- **Estatísticas:** `create_statistics_charts()` lê o `apcac.csv` e visualiza as métricas de área em quatro gráficos de barras do Plotly (valores absolutos e percentuais para o bioma Cerrado e para a zona de influência hidrológica).
- **Interface:** componentes do Streamlit organizam a barra lateral (informações do projeto, seleção de camada, legenda) e o conteúdo principal (mapa, estatísticas, referências).

## Notas de Desenvolvimento
- Processos pesados (leitura de geopackages, parsing de QML, carga de CSVs) usam `@st.cache_data` ou `@st.cache_resource` para reduzir I/O repetido.
- A simplificação geométrica (`simplify_geodataframe`) utiliza tolerância padrão de `0.001` grau para equilibrar fidelidade e desempenho. Ajuste conforme a escala de trabalho.
- As bases cartográficas são obtidas de serviços Esri. Garanta conectividade e respeite os termos de uso.
- Para estender o painel (ex.: novos gráficos ou camadas de contexto), siga o padrão de cache existente e reutilize o mapa de estilos ao colorir novas visualizações.

## Solução de Problemas
- **Erros ao importar libs:** instale as bibliotecas de desenvolvimento do GDAL antes do GeoPandas ou prefira um ambiente `conda-forge`.
- **`apcac.gpkg` não encontrado:** verifique se o diretório `data/` está ao lado de `mapview.py` ou ajuste as constantes `gpkg_path`/`csv_path`.
- **Mapa lento para carregar:** reduza a tolerância de simplificação padrão ou restrinja a extensão exibida; o cache só acelera após a primeira carga.
- **Mapas base indisponíveis:** proxies corporativos ou ambientes offline podem bloquear os tiles da Esri; substitua por `folium.TileLayer('openstreetmap')` se necessário.

## Materiais Relacionados
TODO

## Licença
TODO
