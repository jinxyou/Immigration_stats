# 🇨🇦 Canada Immigration Insights Dashboard

An interactive web dashboard for exploring immigration patterns across Canada using 2021 Canadian Census data. This application provides detailed visualizations of immigrant demographics, origins, and settlement patterns at multiple geographic levels.

## 📊 Features

### Interactive Maps
- **Canada Map**: Click any region to see where its immigrants come from worldwide
- **World Map**: Click any country to see where those immigrants settle in Canada
- **Multiple Geographic Levels**: Explore data at Census Subdivisions (CSD), Census Divisions (CD), and Provincial levels
- **Real-time Filtering**: Filter by immigration status (Total, Immigrants, Non-immigrants, Non-permanent residents)

### Data Visualizations
- **Bar Charts**: Top regions and origins with hover interactions
- **Line Charts**: Immigration timeline analysis for different periods
- **Pie Charts**: Demographic breakdowns by gender, age, and immigration status
- **Intersection Analysis**: Detailed demographic breakdowns when both maps have selections

### Key Statistics
- Total population counts with formatted display (M/K suffixes)
- Immigrant vs non-immigrant population breakdowns
- Origin country diversity metrics
- Real-time calculations based on user selections

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Conda (recommended) or pip

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Immigration_stats
   ```

2. **Create conda environment**
   ```bash
   conda env create -f environment.yml
   conda activate immigration_stats
   ```

3. **Launch the application**
   ```bash
   python app.py
   ```

4. **Access the dashboard**
   - Open your browser and go to `http://localhost:8050`
   - The dashboard will load with interactive maps and visualizations

## 📈 How to Use

### Basic Navigation
1. **Select a Canadian Region**: Click any area on the Canada map to see immigration origins
2. **Choose an Origin Country**: Click any country on the world map to see settlement patterns
3. **Filter by Status**: Use the dropdown to focus on specific immigration categories
4. **Explore Different Levels**: Switch between CSD, CD, and Provincial views

### Advanced Features
- **Hover Interactions**: Hover over map regions to see detailed tooltips
- **Chart Synchronization**: Related charts update automatically based on selections
- **Reset Functionality**: Use the reset button to clear selections
- **Responsive Design**: Works on desktop and tablet devices

## 🗂️ Data Sources

- **Primary Data**: Statistics Canada - [Table 98-10-0307-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=9810030701)
- **Geographic Data**: 
  - Canadian administrative boundaries (CSD, CD, Provinces)
  - World country boundaries with regional groupings
- **Time Period**: 2021 Canadian Census data

## 🛠️ Technical Stack

### Frontend
- **Dash**: Python web framework for building analytical web applications
- **Dash Leaflet**: Interactive mapping components
- **Dash Bootstrap Components**: UI components and styling
- **Dash Vega Components**: Advanced charting with Altair/Vega
- **Bootstrap Icons**: Icon library

### Backend
- **Pandas**: Data manipulation and analysis
- **GeoPandas**: Geographic data processing
- **Altair**: Declarative statistical visualization
- **Flask Caching**: Performance optimization

### Data Processing
- **Parquet Files**: Efficient data storage format
- **GeoJSON**: Geographic data format for mapping
- **JSON**: Data serialization for web components

## 📁 Project Structure

```
Immigration_stats/
├── app.py                 # Main Dash application
├── data/
│   ├── processed/         # Cleaned and processed data
│   │   ├── geojson/       # Geographic boundary files
│   │   └── immigration_data/  # Census data in parquet format
│   └── raw/              # Original data files
├── notebooks/            # Jupyter notebooks for data exploration
├── environment.yml       # Conda environment specification
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## 🔧 Configuration

### Environment Variables
- No environment variables required for basic usage
- Default port: 8050
- Default host: 0.0.0.0 (accessible from network)

### Customization
- Modify `custom_styles` in `app.py` to change visual appearance
- Adjust color scales in the mapping functions
- Update chart configurations in callback functions

## 📊 Data Categories

### Immigration Status
- **Total**: Complete population counts
- **Immigrants**: Permanent residents who immigrated to Canada
- **Non-immigrants**: Canadian-born residents
- **Non-permanent residents**: Temporary residents (students, workers, etc.)

### Geographic Levels
- **Census Subdivisions (CSD)**: Municipalities and local areas
- **Census Divisions (CD)**: Counties and regional districts
- **Provinces**: Provincial and territorial boundaries

### Origin Groupings
- **Countries**: Individual country data
- **Regions**: Continental regions (Europe, Asia, etc.)
- **Continents**: Continental-level aggregations
- **Inside Canada**: Inter-provincial migration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## 👨‍💻 Author

**Eugene You** - [GitHub Profile](https://github.com/jinxyou)

## 🙏 Acknowledgments

- Statistics Canada for providing comprehensive census data
- The Dash community for excellent documentation and examples
- Open source mapping and visualization libraries

---

**Note**: This dashboard is for educational and research purposes. Always refer to official Statistics Canada publications for authoritative demographic information.
