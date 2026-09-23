# Grid Charge

## Smart EV Charging & Localized Grid Management

Grid Charge is an intelligent EV charging and energy-management system designed to coordinate multiple electric vehicles connected to the same residential or commercial charging site.

Instead of allowing every EV to charge independently at maximum power, Grid Charge considers the overall energy situation and intelligently distributes available charging power while respecting the site's electrical capacity.

---

## Problem Statement

As EV adoption increases, multiple EVs may need to charge simultaneously at apartments, offices, malls, hotels, and EV charging hubs.

If every EV charges at maximum power at the same time, the combined demand can exceed the available grid or transformer capacity.

The core energy relationship is:

```text
Building Demand + EV Charging - Solar Generation
                    <=
              Grid Capacity

Our Solution

Grid Charge combines:

Machine learning
Demand forecasting
EV charging optimization
Grid-capacity constraints
Renewable-energy awareness
Site simulation
Real-time-style monitoring
Interactive dashboard visualization

The core architecture is:

ML predicts
     |
     v
Optimization decides
     |
     v
Controller / charging logic acts
     |
     v
Dashboard explains

The goal is to coordinate multiple EVs as a single energy-management problem instead of treating every charger independently.

System Architecture
                         +----------------------+
                         |       EV Fleet       |
                         |----------------------|
                         | SOC                  |
                         | Arrival / Departure  |
                         | Required Energy      |
                         | Charging Limit       |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |   Site Simulation    |
                         |----------------------|
                         | Building Demand      |
                         | Grid Capacity        |
                         | Solar Generation     |
                         | EV Demand            |
                         +----------+-----------+
                                    |
                    +---------------+---------------+
                    |                               |
                    v                               v
          +---------------------+        +---------------------+
          | Building Demand     |        | Current Site       |
          | Forecasting         |        | Conditions         |
          |                     |        |                     |
          | XGBoost             |        | Grid / EV / Solar  |
          +----------+----------+        +----------+----------+
                     |                              |
                     +--------------+---------------+
                                    |
                                    v
                         +----------------------+
                         |  V5 Optimization     |
                         |----------------------|
                         | Charging Allocation  |
                         | EV Priorities        |
                         | Grid Safety          |
                         | Future Demand        |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | Grid Safety /        |
                         | Control Layer        |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |    Grid Charge UI    |
                         |----------------------|
                         | Command Center       |
                         | EV Fleet             |
                         | Charging Sessions    |
                         | Optimization         |
                         | Grid & Energy        |
                         +----------------------+
Key Features
1. Command Center

The Command Center provides a centralized view of the charging site.

It displays information such as:

Active EVs
Total charging demand
Building electricity demand
Available grid capacity
Renewable energy availability
Grid status
Optimization status
Energy flow
2. EV Fleet Monitoring

The EV Fleet section provides information about connected vehicles.

Important EV attributes include:

EV ID
Battery capacity
State of Charge (SOC)
Target SOC
Required energy
Maximum charging power
Arrival time
Departure time
Charging status
3. Charging Session Monitoring

Charging sessions can be monitored using information such as:

EV
Charging power
Energy delivered
Charging progress
Session status
Required energy
Charging time
4. Smart Charging Optimization

The optimization layer distributes available charging power among multiple EVs.

It considers:

Current SOC
Departure time
Required energy
EV charging limits
Building electricity demand
Available grid capacity
Renewable energy availability
Future predicted demand

The objective is to satisfy as much EV charging demand as possible while maintaining site-level electrical safety.

5. Building Demand Forecasting

Grid Charge uses machine learning to forecast future building electricity demand.

The current forecasting model is:

XGBoost Regressor

The model predicts building electricity demand as a continuous numerical value.

The forecast is then provided to the optimization layer for look-ahead charging decisions.

6. Grid and Energy Monitoring

The system monitors:

Building demand
EV charging demand
Grid capacity
Available grid capacity
Solar generation
Net site demand
Grid safety

This allows the operator to understand the site's energy condition before and during EV charging.

7. Renewable Energy Awareness

Solar generation is included in the site energy model.

The optimization system can account for available renewable energy while allocating charging power.

This allows EV charging to make better use of available clean energy without intentionally violating the site's grid constraints.

8. Grid Safety

Grid capacity is treated as a hard safety constraint.

The fundamental relationship is:

Building Demand
+
EV Charging
-
Solar Generation
<=
Grid Capacity

The optimization process therefore attempts to keep controlled site demand within the available grid limit.

9. Forecast-Aware Look-Ahead Optimization

The V5 optimization approach does not consider only the current interval.

It also considers future predicted building demand and competing EV charging requirements.

This allows the system to plan charging across future time intervals.

Conceptually:

Current Site Conditions
          +
Future Building Demand
          +
Future EV Requirements
          |
          v
Better Charging Allocation
10. What-If and Stress Simulation

The project can be evaluated under difficult energy conditions.

Examples include:

Increased building demand
Reduced solar generation
Reduced grid capacity
Increased EV charging requirements

This allows the charging strategy to be stress-tested without connecting the system to physical electrical infrastructure.

Machine Learning
Model Used

Grid Charge currently uses:

XGBoost Regressor

The forecasting problem is treated as a supervised regression problem because the target is a continuous building electricity-demand value.

Why XGBoost?

XGBoost was selected because it:

Works well with structured and tabular data
Can model nonlinear relationships
Can capture feature interactions
Performs well for regression problems
Is efficient to train
Can be saved and reused for inference
Dataset

For building-demand forecasting, Grid Charge uses the:

UCI Individual Household Electric Power Consumption Dataset

The dataset contains historical electricity-consumption measurements.

Important Data Separation

Different data sources are used for different components of the project.

Historical Real-World Data

The UCI dataset is used for:

Building Electricity Demand Forecasting
Synthetic / Simulated Data

The EV and site-management components use simulated scenarios for:

EV arrivals
EV departures
Battery SOC
Required charging energy
EV charging limits
Grid capacity
Solar generation
Site conditions
Optimization testing

Therefore, the project does not claim that the UCI dataset is an EV charging dataset.

For a real deployment, the forecasting model could be retrained using historical smart-meter data from the actual building or charging site.

Machine Learning Results

The current XGBoost building-demand model achieved:

Metric	XGBoost
MAE	0.2685 kW
RMSE	0.4434
R2	0.7180

A naive baseline achieved:

Metric	Baseline
MAE	0.2899 kW
RMSE	0.5031
R2	0.6370

The XGBoost model reduced MAE by approximately 7.40% compared with the naive baseline.

Note: R2 is a statistical evaluation metric and should not be interpreted as simple prediction accuracy.

V5 Optimization

The current V5 optimization scenario uses:

50 EVs
112 grid intervals
1,205 optimization decision records
250 kW grid limit

The optimizer considers EV requirements together with site-level electrical constraints.

V5 Results
Metric	Result
EVs simulated	50
Grid intervals	112
Optimization decisions	1,205
Average completion	98.30%
EVs completed	47 / 50
Unmet energy	22.63 kWh
Peak EV charging	133.14 kW
Peak controlled site demand	250.00 kW
Grid-safe intervals	112 / 112
EV capacity violations	0

The results demonstrate the trade-off between maximizing EV charging completion and maintaining strict grid-capacity constraints.

Stress Testing

The optimization system was also evaluated under a more constrained scenario.

The stress scenario applied:

Building Demand x 1.7
Solar Generation x 0.5
Grid Limit x 0.9

The resulting stress-test metrics were:

Metric	Stress Scenario
Delivered EV energy	245.42 kWh
Average completion	22.35%
Completed EVs	1
Deadline misses	49
Maximum controlled overload	67.27 kW
Grid-safe intervals	75 / 112
EV capacity violations	0

The stress scenario demonstrates that severe building-level demand can become the limiting factor even when the EV controller itself respects EV charging constraints.

ML and Optimization Workflow

The overall workflow is:

Historical Electricity Data
            |
            v
    Data Preprocessing
            |
            v
     XGBoost Forecast
            |
            v
   Future Demand Forecast
            |
            +----------------------+
            |                      |
            v                      v
     Current Site State       EV Requirements
            |                      |
            +----------+-----------+
                       |
                       v
              V5 Optimization
                       |
                       v
             EV Charging Power
                       |
                       v
              Grid Safety Check
                       |
                       v
                  Dashboard
Frontend

The Grid Charge frontend is a lightweight web application built using:

HTML
CSS
JavaScript

The interface is designed as an operator dashboard for monitoring the charging site.

Main Interface Areas
Command Center
EV Fleet
Charging Sessions
Optimization
Grid & Energy
Site Assessment
What-If Simulation
System Information
About

The frontend communicates with the FastAPI backend through HTTP REST APIs.

Backend

The backend is built using:

Python
FastAPI
Uvicorn

The backend exposes REST APIs for:

EV information
Grid information
Demand forecasts
Optimization results
Dashboard data
Health monitoring

The current dashboard backend is primarily artifact-backed using validated V5 simulation outputs.

API Endpoints
Health
GET /api/health
EVs
GET /api/evs
GET /api/evs/{ev_id}
Grid
GET /api/grid
GET /api/grid/latest
GET /api/grid/summary
Forecast
GET /api/forecast
GET /api/forecast/sample
Optimization
GET /api/optimization
GET /api/optimization/decisions
GET /api/optimization/decisions/latest
GET /api/optimization/ev/{ev_id}
Dashboard
GET /api/dashboard
API Documentation

FastAPI provides interactive API documentation through:

http://127.0.0.1:8000/docs
Project Structure
smart-ev-charging/
|
+-- backend/
|   +-- database/
|   +-- routes/
|   +-- services/
|   +-- main.py
|
+-- data/
|   +-- raw/
|   +-- processed/
|   +-- synthetic/
|   +-- smart_ev.db
|
+-- frontend/
|   +-- grid-charge/
|       +-- GridCharge.html
|       +-- publish.html
|       +-- src/
|           +-- api.js
|           +-- app.js
|           +-- body.html
|           +-- build.py
|           +-- charts.js
|           +-- data.js
|           +-- hero.js
|           +-- pages.js
|           +-- styles.css
|           +-- theme.css
|
+-- ml/
|   +-- eda_building_demand.py
|   +-- preprocess_uci.py
|   +-- train_building_demand_model.py
|   +-- train_random_forest.py
|
+-- models/
|   +-- building_demand_xgboost.joblib
|   +-- building_demand_features.joblib
|
+-- optimization/
|   +-- ev_optimizer.py
|
+-- simulation/
|   +-- realtime_controller.py
|   +-- site_demand_forecast.py
|   +-- site_simulator.py
|   +-- ...
|
+-- .gitignore
+-- README.md
Technology Stack
Category	Technology
Frontend	HTML, CSS, JavaScript
Backend	Python, FastAPI
Server	Uvicorn
Machine Learning	XGBoost, Scikit-learn
Data Processing	Pandas, NumPy
Model Persistence	Joblib
Database	SQLite, SQLAlchemy
Visualization	JavaScript Charts
Simulation	Python, Pandas, NumPy
API Communication	REST / HTTP
Running the Project
1. Clone the Repository

Clone the Grid Charge repository from GitHub and enter the project directory.

git clone <your-grid-charge-github-repository>
cd grid-charge
2. Create the Python Environment

On Windows:

python -m venv .venv

Activate the environment:

.\.venv\Scripts\Activate.ps1
3. Install Dependencies

Install the required Python packages for the backend and machine-learning environment.

The main technologies used by the project include:

pandas
numpy
scikit-learn
xgboost
fastapi
uvicorn
joblib
sqlalchemy
4. Start the FastAPI Backend

From the project root:

python -m uvicorn backend.main:app --reload --port 8000

The backend will run at:

http://127.0.0.1:8000

API documentation:

http://127.0.0.1:8000/docs
5. Start the Frontend

Open another terminal:

cd frontend/grid-charge
python -m http.server 5500

Then open:

http://127.0.0.1:5500/GridCharge.html
Real-World Applications

Grid Charge can be applied to several types of EV charging environments.

Residential Communities

Multiple residents may charge their EVs using a shared electrical connection.

Grid Charge can coordinate charging to reduce the possibility of exceeding local electrical capacity.

Offices

Employee EV charging can be coordinated alongside normal office electricity consumption.

The system can consider building demand while allocating available charging power.

Shopping Malls

Multiple EV chargers can be managed together with the mall's existing electrical demand.

Hotels

EV charging can be coordinated according to vehicle requirements and expected departure times.

EV Charging Hubs

Multiple charging points can be coordinated as one energy-management system instead of treating every charger independently.

Why Grid Charge?

A conventional charging approach primarily focuses on an individual vehicle:

Can this EV charge now?

Grid Charge addresses a larger system-level question:

How should multiple EVs share limited electrical capacity?

The system combines:

Demand Forecasting
        +
EV Requirements
        +
Charging Optimization
        +
Grid Constraints
        +
Renewable Energy
        +
Monitoring

This makes Grid Charge an energy-management layer for coordinated EV charging rather than only an individual charging interface.

Current Limitations

The current version is a software prototype and simulation-based system.

Important limitations include:

EV charging scenarios are simulated.
Solar generation scenarios are simulated.
Grid-capacity scenarios are simulated.
The UCI dataset represents historical household electricity consumption rather than EV charging data.
The current forecasting model is not trained on live data from a deployed target building.
Physical EV chargers / EVSE hardware are not directly connected.
Smart-meter hardware integration is not currently implemented.
The main dashboard currently consumes prepared V5 simulation artifacts rather than live electrical hardware measurements.

These limitations are important when interpreting the current results.

Future Scope

Future versions of Grid Charge can include:

Real EVSE integration
Smart-meter integration
Live building electricity data
Site-specific demand forecasting
Live solar generation data
Weather-aware solar forecasting
Uncertainty-aware demand forecasting
Larger multi-site optimization
Dynamic electricity-price optimization
Battery degradation awareness
Vehicle-to-Grid (V2G)
IoT-based charging controllers
Production-grade database infrastructure
Cloud deployment
Multi-location charging management
Project Vision

Grid Charge aims to provide an intelligent energy-management layer for EV charging infrastructure.

Instead of treating each EV charger independently, the system considers the entire site.

                     GRID CHARGE
                          |
                          v
              +----------------------+
              |   Site Energy State  |
              +----------+-----------+
                         |
                         v
              +----------------------+
              | Building Demand      |
              | Forecasting           |
              +----------+-----------+
                         |
                         v
              +----------------------+
              | EV Requirements      |
              +----------+-----------+
                         |
                         v
              +----------------------+
              | Smart Optimization   |
              +----------+-----------+
                         |
                         v
              +----------------------+
              | Safe Charging Plan   |
              +----------+-----------+
                         |
                         v
              +----------------------+
              | Dashboard Monitoring |
              +----------------------+
Core Architecture

ML predicts -> Optimization decides -> Controller acts -> Dashboard explains.

Project Status

Current implementation includes:

 Building-demand forecasting
 XGBoost model
 EV charging simulation
 Grid-demand simulation
 Solar-generation simulation
 V5 forecast-aware optimization
 Grid safety constraints
 FastAPI backend
 REST APIs
 Grid Charge frontend
 Command Center dashboard
 EV Fleet monitoring
 Charging Session monitoring
 Optimization monitoring
 Grid and Energy monitoring
 Stress testing
 GitHub repository
Summary

Grid Charge is a software prototype for intelligent EV charging coordination.

It combines:

Machine Learning
       +
Demand Forecasting
       +
Optimization
       +
EV Charging Simulation
       +
Grid Constraints
       +
Renewable Energy
       +
Interactive Monitoring

The project demonstrates how machine learning and optimization can work together to coordinate multiple EV charging sessions while considering the limited electrical capacity of a shared charging site.              