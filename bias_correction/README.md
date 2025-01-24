# Bias Correction for Cropland Area Estimation

This package implements the Olofsson et al. (2014) methodology for bias-adjusted area estimation using stratified sampling. It was developed to process cropland extent analysis across the North American Central Flyway region, specifically handling both Great Plains and Southern (Mexican) subregions.

## Methods

The package implements a stratified sampling approach for bias correction of cropland area estimates. Following Olofsson et al. (2014), it:
- Calculates error-adjusted area estimates for cropland and non-cropland
- Accounts for commission and omission errors
- Weighs by proportional area of each stratum
- Computes uncertainty estimates

The methodology was applied independently to two subregions (Great Plains and Southern) and then combined to generate final area estimates and associated uncertainties for the entire study area.


## Workflow Diagram 

```mermaid 
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#b3e0ff',
    'primaryTextColor': '#000',
    'primaryBorderColor': '#7AA7C7',
    'lineColor': '#7AA7C7',
    'secondaryColor': '#ffe0b3',
    'tertiaryColor': '#fff',
    'fontSize': '20px'
  }
}}%%

subgraph InputData[" 📊 INPUT DATA                                                                                          "]
        direction LR
        style InputData fill:#e6f3ff,stroke:#7AA7C7,stroke-width:4px

        TotalArea["Total Cropland<br/><i>Annual area estimates<br/>by region</i>"]
        ActiveArea["Active Cropland<br/><i>Annual area estimates<br/>by region</i>"]
        ValidationData["Validation Samples<br/><i>Visual interpretation<br/>of cropland presence</i>"]
        StrataProp["Strata Information<br/><i>Regional sampling<br/>proportions</i>"]

        TotalArea --- ActiveArea
        ActiveArea --- ValidationData
        ValidationData --- StrataProp
    end


    subgraph Process[" ⚙️ SPLIT SUBREGIONS"]
        direction TB
        style Process fill:#fff5e6,stroke:#D4A76A,stroke-width:15px
        
        Split["Split Data by Region"]
        
        subgraph RegionalAnalysis["Regional Analysis"]
            direction LR
            
            subgraph GreatPlains["Great Plains Analysis"]
                direction TB
                style GreatPlains fill:#fffbf0,stroke:#D4A76A,stroke-width:2px
                
                GP_Comm["Commission/Omission<br/>Error Rates"] & GP_SE["Standard Error<br/>Calculation"] --> GP_Calc["Calculate Area<br/>Adjustments"]
            end
            
            subgraph Mexico["Mexico Analysis"]
                direction TB
                style Mexico fill:#fffbf0,stroke:#D4A76A,stroke-width:2px
                
                MX_Comm["Commission/Omission<br/>Error Rates"] & MX_SE["Standard Error<br/>Calculation"] --> MX_Calc["Calculate Area<br/>Adjustments"]
            end
        end

        Split --> GreatPlains
        Split --> Mexico
    end

    subgraph Results["📈 RESULTS"]
        direction TB
        style Results fill:#e6ffe6,stroke:#79B779,stroke-width:4px
        
        Combine["Combine Regional<br/>Results"]
        Uncertainty["Propagate<br/>Uncertainty"]
        Final["Generate Final<br/>Estimates"]
        
        Combine --> Uncertainty --> Final
    end

    InputData --> Split
    GP_Calc & MX_Calc --> Combine

    classDef default fontSize:16px;
    classDef process fill:#f9f9f9,stroke:#666,stroke-width:2px,fontSize:18px;
    classDef box fill:#fff,stroke:#333,stroke-width:2px,fontSize:18px;
```

## Installation

```bash
pip install git+https://github.com/COYE-Coder/Crop-Scope/main/bias_correction.git
```


## Usage

```import bias_correction as bc

# Process both total and active footprints
results = bc.process_footprint(
    gross_df=window_gross_df,
    net_df=window_net_df,
    gp_accuracy_df=gp_accuracy_df,
    mx_accuracy_df=mx_accuracy_df,
    gp_strata_proportions=bc.GP_STRATA_PROPORTIONS,
    mx_strata_proportions=bc.MX_STRATA_PROPORTIONS,
    gp_overlap_areas=bc.GP_OVERLAP_AREAS,
    mx_overlap_areas=bc.MX_OVERLAP_AREAS,
    years=bc.YEARS
)

# Create visualization
bc.create_multipanel_plot(results, save_path='trends.png')
```


See `demo.ipynb` for a complete example.

## Citation
If you use this code in your research, please cite:
[]


## References
Olofsson, P., Foody, G. M., Herold, M., Stehman, S. V., Woodcock, C. E., & Wulder, M. A. (2014). Good practices for estimating area and assessing accuracy of land change. Remote Sensing of Environment, 148, 42-57.
