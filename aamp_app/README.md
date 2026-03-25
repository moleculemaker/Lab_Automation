# Lab Automation Dash App

A multi-page interactive dashboard built with **Dash** for automating multiple devices or instruments capable of being controlled. It can be combined with optimization algorithms for autonomous process optimization.

---

## Pages Overview

### Home Page

**File:** `app.py`

**Description:**  
The landing page of the app providing an index of the pages.

---

### Sampler Page

**File:** `pages/sampler.py`

**Description:**  
Provides setup for campaigns. The process is as such: **naming of the campaign** -> **set boundaries for each parameter sets like temperature, concentration, printing gap** -> **generate initial parameters** -> **save the parameters into the database for future use**.

**Features:**
- Sobol sampling
- Random sampling
- Umap
- PCA

---

### Recipe Builder Page

**File:** `pages/recipe-builder.py`

**Description:**  
Used to construct executable recipes that define how devices or instruments should operate during experiments. The process is as such: **select campaign** -> **enter the position of each parameter setup in the solution map** -> **generate the recipe for each parameter set** -> **execute the recipe**.

**Features:**
- Step-by-step recipe configuration
- Parameter-to-instruction mapping
- Reusable recipe templates

---

### Solution Map Page

**File:** `pages/solution-map.py`

**Description:**  
Marks the position of each parameter set in the device. Users can munually update the solution map and save it into the dateabase, which will be used by the recipe builder.

---

### Autonomous Run Page

**File:** `pages/bayesian-optimization.py`

**Description:**  
Enables autonomous experimentation using optimization algorithms such as Bayesian optimization. The system iteratively proposes new parameter sets for new experiments based on prior results given by the image processor to efficiently converge toward optimal conditions. Use this page after creating the campaign on the sampler page.

**Features:**
- Bayesian optimization loop
- Image processing and analysis
- Real-time updating with new experimental data and plots

---

### Manual Run Page

**File:** `pages/manual-run.py`

**Description:**  
Allows users to manually execute experiments by separating each step in the autonomous run.

**Features:**
- Bayesian optimization loop
- Image processing and analysis

---

### Database Browser Page (still in progress)

**File:** `pages/database.py`

**Description:**  
Provides an interface for browsing, querying, and managing stored experimental data, campaigns, and results. Users can review past experiments and reuse data for further analysis or optimization.

---