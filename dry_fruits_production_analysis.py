"""Analyze FAOSTAT dry-fruit production and forecast country-item output."""

# =============================================================================
# Global Dry Fruits Production Analysis and Prediction Using Machine Learning
# GOOGLE COLAB VERSION: paste in ONE cell, run, upload the CSV when asked.
# (If xgboost is missing run first:  !pip install -q xgboost)
# Dataset: FAOSTAT QCL export (Area harvested / Yield / Production, 2000-2024)
# =============================================================================
import os, warnings, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from scipy.stats import t as student_t
from xgboost import XGBRegressor

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid", context="notebook")
RS = 42

# --- Colab: upload the FAOSTAT CSV when prompted; local runs use the organized raw-data path ---
try:
    from google.colab import files
    IN_COLAB = True
    print("Upload your FAOSTAT CSV file:")
    uploaded = files.upload()
    CSV_PATH = list(uploaded.keys())[0]
    OUT = "/content/outputs"
except ImportError:
    IN_COLAB = False
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
    CSV_PATH = os.environ.get(
        "FAOSTAT_CSV",
        os.path.join(PROJECT_DIR, "data", "raw", "DRY FRUIT COUNTRY WISE.csv"),
    )
    OUT = os.environ.get("DRY_FRUITS_OUTPUT_DIR", os.path.join(PROJECT_DIR, "outputs"))
FIG = os.path.join(OUT, "figures")
os.makedirs(FIG, exist_ok=True)

def savefig(name):
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, f"{name}.png"), dpi=150)
    if IN_COLAB:
        plt.show()
    plt.close()

# =============================================================================
# STEP 1 - DATA UNDERSTANDING (inspect the raw file, keep it untouched)
# =============================================================================
raw = pd.read_csv(CSV_PATH, encoding="utf-8-sig")   # utf-8-sig strips the BOM
clean_columns = {"Country", "Dry_Fruit", "Year", "Area_Harvested", "Production", "Yield"}
if clean_columns.issubset(raw.columns):
    raw = raw.melt(
        id_vars=["Country", "Dry_Fruit", "Year"],
        value_vars=["Area_Harvested", "Production", "Yield"],
        var_name="Element",
        value_name="Value",
    )
    raw = raw.rename(columns={"Country": "Area", "Dry_Fruit": "Item"})
    raw["Element"] = raw["Element"].replace({"Area_Harvested": "Area harvested"})
    raw["Flag Description"] = np.nan
    raw["Unit"] = raw["Element"].map({
        "Area harvested": "ha",
        "Production": "tonnes",
        "Yield": "kg/ha",
    })
print("=== STEP 1: RAW DATA ===")
print("Rows, columns      :", raw.shape)
print("Column names       :", list(raw.columns))
print("\nData types:\n", raw.dtypes)
print("\nMissing values:\n", raw.isna().sum())
print("\nDuplicate rows     :", raw.duplicated().sum())
print("Unique areas       :", raw["Area"].nunique())
print("Unique items       :", raw["Item"].nunique(), sorted(raw["Item"].unique()))
print("Years              :", raw["Year"].min(), "-", raw["Year"].max(), f"({raw['Year'].nunique()} years)")
print("Elements/units     :", raw.groupby("Element")["Unit"].unique().to_dict())
print("Flags              :", raw["Flag Description"].value_counts().to_dict())
print("\nDescriptive statistics of Value by Element:\n",
      raw.groupby("Element")["Value"].describe().round(2))

# =============================================================================
# STEP 2 - DATA CLEANING (raw is preserved; `df` is the clean modelling frame)
# =============================================================================
# 2a. Keep only needed columns. Domain/codes/Unit/Note are constant or redundant;
#     the Flag is kept only to drop "Missing value; data cannot exist" rows.
d = raw[["Area", "Item", "Element", "Year", "Value", "Flag Description"]].copy()
d.columns = ["Country", "Dry_Fruit", "Element", "Year", "Value", "Flag"]

# 2b. Missing values: every NaN Value carries flag "Missing value; data cannot exist".
#     There is nothing to impute (not a zero, not unknown) -> drop these rows.
n_missing = d["Value"].isna().sum()
d = d.dropna(subset=["Value"])

# 2c. "China" is an FAO aggregate that overlaps "China, mainland" (+ Taiwan etc.).
#     Keeping all would double count China -> drop the aggregate, keep its parts.
d = d[d["Country"] != "China"]

# 2d. Standardise names ("Almonds, in shell" -> "Almonds"; shorten long country names)
d["Dry_Fruit"] = d["Dry_Fruit"].str.replace(", in shell", "", regex=False)
d["Country"] = d["Country"].replace({
    "United States of America": "USA", "Iran (Islamic Republic of)": "Iran",
    "Russian Federation": "Russia", "Netherlands (Kingdom of the)": "Netherlands",
    "United Kingdom of Great Britain and Northern Ireland": "UK",
    "China, mainland": "China (mainland)", "China, Taiwan Province of": "Taiwan",
    "Bolivia (Plurinational State of)": "Bolivia", "Venezuela (Bolivarian Republic of)": "Venezuela",
    "United Republic of Tanzania": "Tanzania", "Republic of Korea": "South Korea",
    "Democratic People's Republic of Korea": "North Korea", "Republic of Moldova": "Moldova",
    "Syrian Arab Republic": "Syria"})

# 2e. Restrict to dry fruits / nuts. The file also holds Grapes, Plums and Apricots,
#     but these are FRESH-fruit items here (dried forms such as raisins/prunes are not
#     in the file), so they are excluded. Dates and Figs are kept (commonly consumed
#     dried). Change DRY_FRUITS below to widen/narrow the scope.
DRY_FRUITS = ["Almonds", "Walnuts", "Cashew nuts", "Hazelnuts", "Pistachios",
              "Chestnuts", "Brazil nuts", "Dates", "Figs"]
d = d[d["Dry_Fruit"].isin(DRY_FRUITS)]

# 2f. Duplicates on the natural key (Country, Dry_Fruit, Element, Year)
n_dup = d.duplicated(subset=["Country", "Dry_Fruit", "Element", "Year"]).sum()
d = d.drop_duplicates(subset=["Country", "Dry_Fruit", "Element", "Year"])

# 2g. Long -> wide: one row per Country x Dry_Fruit x Year
df = (d.pivot(index=["Country", "Dry_Fruit", "Year"], columns="Element", values="Value")
        .reset_index().rename(columns={"Area harvested": "Area_Harvested"}))
df.columns.name = None

# 2h. Numeric types + impossible values check
for c in ["Production", "Area_Harvested", "Yield"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")
n_neg = int((df[["Production", "Area_Harvested", "Yield"]] < 0).sum().sum())
df = df[~((df[["Production", "Area_Harvested", "Yield"]] < 0).any(axis=1))]

# 2i. Yield is by definition Production/Area. If Yield is missing but both others
#     exist (Area>0), recompute it (kg/ha = t*1000/ha). Not invented data.
m = df["Yield"].isna() & df["Production"].notna() & (df["Area_Harvested"] > 0)
df.loc[m, "Yield"] = df.loc[m, "Production"] * 1000 / df.loc[m, "Area_Harvested"]
n_yield_filled = int(m.sum())

# 2j. Rows without Production are useless for EDA/target -> drop. Zeros are kept
#     (a real recorded zero, e.g. crop failure); they are handled in MAPE later.
df = df.dropna(subset=["Production"])
df = df.sort_values(["Country", "Dry_Fruit", "Year"]).reset_index(drop=True)
df.to_csv(os.path.join(OUT, "clean_dry_fruits_data.csv"), index=False)

print("\n=== STEP 2: CLEANING SUMMARY ===")
print(f"NaN-value rows dropped (cannot exist): {n_missing}")
print(f"Duplicate keys removed               : {n_dup}")
print(f"Negative values found                : {n_neg}")
print(f"Yield recomputed from Prod/Area      : {n_yield_filled}")
print(f"Zero-production rows kept            : {(df['Production'] == 0).sum()}")
print(f"Clean frame: {df.shape}, {df['Country'].nunique()} countries, "
      f"{df['Dry_Fruit'].nunique()} dry fruits, years {df['Year'].min()}-{df['Year'].max()}")
print("Remaining NaN:\n", df.isna().sum())

# =============================================================================
# STEP 3 - EXPLORATORY DATA ANALYSIS
# =============================================================================
print("\n=== STEP 3: EDA ===")
LAST = df["Year"].max()
tot_c = df.groupby("Country")["Production"].sum().sort_values(ascending=False)
tot_f = df.groupby("Dry_Fruit")["Production"].sum().sort_values(ascending=False)
print("Top 5 countries:\n", tot_c.head(5).round(0)); print("Fruits:\n", tot_f.round(0))

# 1 Top countries
plt.figure(figsize=(9, 6))
sns.barplot(x=tot_c.head(10).values / 1e6, y=tot_c.head(10).index, color="#2a7f62")
plt.title("Top 10 Countries by Cumulative Dry-Fruit Production (2000-2024)")
plt.xlabel("Total production (million tonnes)"); plt.ylabel("Country"); savefig("01_top_countries")

# 2 Top dry fruits
plt.figure(figsize=(9, 5))
sns.barplot(x=tot_f.values / 1e6, y=tot_f.index, color="#c8863a")
plt.title("Cumulative Production by Dry Fruit (2000-2024)")
plt.xlabel("Total production (million tonnes)"); plt.ylabel("Dry fruit"); savefig("02_top_fruits")

# 3 Global trend
g = df.groupby("Year")["Production"].sum() / 1e6
plt.figure(figsize=(9, 5)); plt.plot(g.index, g.values, marker="o", label="Global production")
plt.title("Global Dry-Fruit Production by Year"); plt.xlabel("Year")
plt.ylabel("Production (million tonnes)"); plt.legend(); savefig("03_global_trend")

# 4 Individual fruit trends
pf = df.pivot_table(index="Year", columns="Dry_Fruit", values="Production", aggfunc="sum") / 1e6
pf.plot(figsize=(10, 6), marker=".", logy=True)
plt.title("Production Trend of Each Dry Fruit (log scale)"); plt.xlabel("Year")
plt.ylabel("Production (million tonnes, log)"); plt.legend(title="Dry fruit", bbox_to_anchor=(1, 1)); savefig("04_fruit_trends")

# 5 Top producers per fruit
major = tot_f.head(6).index
fig, axes = plt.subplots(2, 3, figsize=(15, 8))
for ax, fr in zip(axes.ravel(), major):
    t = df[df.Dry_Fruit == fr].groupby("Country")["Production"].sum().nlargest(5) / 1e6
    sns.barplot(x=t.values, y=t.index, ax=ax, color="#4a6fa5")
    ax.set_title(fr); ax.set_xlabel("Total production (million t)"); ax.set_ylabel("Country")
fig.suptitle("Top 5 Producing Countries for the 6 Major Dry Fruits (2000-2024)", y=1.01)
savefig("05_top_countries_per_fruit")

# 6 Area vs production
s = df[(df.Area_Harvested > 0) & (df.Production > 0)]
plt.figure(figsize=(9, 6))
sns.scatterplot(data=s, x="Area_Harvested", y="Production", hue="Dry_Fruit", alpha=.5, s=18)
plt.xscale("log"); plt.yscale("log"); plt.title("Area Harvested vs Production (log-log)")
plt.xlabel("Area harvested (ha, log)"); plt.ylabel("Production (tonnes, log)")
plt.legend(title="Dry fruit", bbox_to_anchor=(1, 1)); savefig("06_area_vs_production")

# 7 Yield vs production
s2 = df[(df.Yield > 0) & (df.Production > 0)]
plt.figure(figsize=(9, 6))
sns.scatterplot(data=s2, x="Yield", y="Production", hue="Dry_Fruit", alpha=.5, s=18)
plt.xscale("log"); plt.yscale("log"); plt.title("Yield vs Production (log-log)")
plt.xlabel("Yield (kg/ha, log)"); plt.ylabel("Production (tonnes, log)")
plt.legend(title="Dry fruit", bbox_to_anchor=(1, 1)); savefig("07_yield_vs_production")

# 8 Correlation heatmap (log1p to reduce skew)
corr = np.log1p(df[["Production", "Area_Harvested", "Yield"]].dropna()).corr()
plt.figure(figsize=(6, 5)); sns.heatmap(corr, annot=True, fmt=".2f", cmap="YlGnBu", vmin=-1, vmax=1)
plt.title("Correlation Heatmap (log1p-transformed)"); plt.xlabel("Variable"); plt.ylabel("Variable")
savefig("08_correlation_heatmap")

# 9 Yearly growth
gr = (g.pct_change() * 100).dropna()
plt.figure(figsize=(10, 5))
plt.bar(gr.index, gr.values, color=np.where(gr.values >= 0, "#2a7f62", "#b5483a"), label="YoY growth")
plt.axhline(0, color="k", lw=.8); plt.title("Year-over-Year Growth of Global Dry-Fruit Production")
plt.xlabel("Year"); plt.ylabel("Growth (%)"); plt.legend(); savefig("09_yearly_growth")

# 10 Country comparison (top 8 countries over time)
top8 = tot_c.head(8).index
pc = df[df.Country.isin(top8)].pivot_table(index="Year", columns="Country", values="Production", aggfunc="sum") / 1e6
pc.plot(figsize=(10, 6), marker=".")
plt.title("Country-wise Production Comparison (Top 8 Countries)"); plt.xlabel("Year")
plt.ylabel("Production (million tonnes)"); plt.legend(title="Country", bbox_to_anchor=(1, 1)); savefig("10_country_comparison")

# =============================================================================
# STEP 4 - FEATURE ENGINEERING (lags only; no same-year information)
# =============================================================================
# Build a complete Year grid (2000..LAST+1) for every Country x Dry_Fruit series so
# shift(k) really means "k calendar years earlier" (not "k rows earlier"), then
# create lags. Rows whose lag years are missing get NaN and are excluded.
years = np.arange(df["Year"].min(), LAST + 2)
pairs = df[["Country", "Dry_Fruit"]].drop_duplicates()
grid = (pairs.merge(pd.DataFrame({"Year": years}), how="cross")
             .merge(df, on=["Country", "Dry_Fruit", "Year"], how="left")
             .sort_values(["Country", "Dry_Fruit", "Year"]).reset_index(drop=True))
grp = grid.groupby(["Country", "Dry_Fruit"])
for k in (1, 2, 3):
    grid[f"Production_lag_{k}"] = grp["Production"].shift(k)
    grid[f"Area_lag_{k}"] = grp["Area_Harvested"].shift(k)
    grid[f"Yield_lag_{k}"] = grp["Yield"].shift(k)
LAGS = [f"{v}_lag_{k}" for v in ("Production", "Area", "Yield") for k in (1, 2, 3)]
CAT = ["Country", "Dry_Fruit"]
FEATURES = CAT + LAGS                     # NOTE: no current-year Area/Yield/Production

model_df = grid.dropna(subset=["Production"] + LAGS)[["Country", "Dry_Fruit", "Year", "Production"] + LAGS]
forecast_df = grid[(grid.Year == LAST + 1)].dropna(subset=LAGS)   # next-year rows (target unknown)
model_df.to_csv(os.path.join(OUT, "model_ready_dataset.csv"), index=False)
print("\n=== STEP 4: FEATURES ===")
print(f"Model-ready rows: {len(model_df)} (from {len(df)} clean rows); "
      f"series: {model_df.groupby(CAT).ngroups}; forecastable for {LAST+1}: {len(forecast_df)}")

# =============================================================================
# STEP 5 - CHRONOLOGICAL SPLIT
# =============================================================================
# Random splitting would put 2023 rows in training and 2019 rows in test, letting the
# model "see the future" and inflating scores. Forecasting must train on the past and
# be evaluated on later years, exactly as it will be used.
TRAIN_END = 2021
train = model_df[model_df.Year <= TRAIN_END].reset_index(drop=True)
test = model_df[model_df.Year > TRAIN_END].reset_index(drop=True)
X_tr, y_tr, X_te, y_te = train[FEATURES], train["Production"], test[FEATURES], test["Production"]
print("\n=== STEP 5: SPLIT ===")
print(f"Train: {len(train)} rows, target years {train.Year.min()}-{train.Year.max()}")
print(f"Test : {len(test)} rows, target years {test.Year.min()}-{test.Year.max()}")
folds = []
for validation_start in (2014, 2016, 2018, 2020):
    training_indices = train.index[train.Year < validation_start]
    validation_indices = train.index[
        (train.Year >= validation_start) & (train.Year < validation_start + 2)
    ]
    folds.append((training_indices.to_numpy(), validation_indices.to_numpy()))

# =============================================================================
# STEP 6 - MODELS + METRICS
# =============================================================================
def make_pipe(model):
    # One-hot for Country/Dry_Fruit (unknown categories ignored); lags pass through
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CAT)],
                            remainder="passthrough")
    return Pipeline([("pre", pre), ("model", model)])

def metrics(y, p):
    y, p = np.asarray(y), np.asarray(p)
    nz = y > 0                                        # MAPE undefined when actual = 0
    return {"MAE": mean_absolute_error(y, p), "RMSE": np.sqrt(mean_squared_error(y, p)),
            "R2": r2_score(y, p), "MAPE_%": np.mean(np.abs((y[nz] - p[nz]) / y[nz])) * 100,
            "WAPE_%": np.abs(y - p).sum() / y.sum() * 100}

rf = make_pipe(RandomForestRegressor(n_estimators=300, random_state=RS, n_jobs=-1))
xgb = make_pipe(XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=6, subsample=.8,
                             colsample_bytree=.8, random_state=RS, n_jobs=-1))
candidate_models = {"Random Forest": rf, "XGBoost": xgb}
cv_actual = []
cv_predictions = {name: [] for name in candidate_models}
cv_naive_predictions = []
for training_indices, validation_indices in folds:
    fold_train = train.loc[training_indices]
    fold_validation = train.loc[validation_indices]
    cv_actual.append(fold_validation["Production"].to_numpy())
    cv_naive_predictions.append(fold_validation["Production_lag_1"].to_numpy())
    for name, candidate in candidate_models.items():
        fold_model = clone(candidate)
        fold_model.fit(fold_train[FEATURES], fold_train["Production"])
        cv_predictions[name].append(
            np.clip(fold_model.predict(fold_validation[FEATURES]), 0, None)
        )
cv_actual = np.concatenate(cv_actual)
cv_naive_predictions = np.concatenate(cv_naive_predictions)
model_selection_metrics = {
    name: metrics(cv_actual, np.concatenate(fold_predictions))
    for name, fold_predictions in cv_predictions.items()
}
model_selection_metrics["Previous-year baseline"] = metrics(
    cv_actual, cv_naive_predictions
)
selection_table = pd.DataFrame(model_selection_metrics).T
selection_table.round(4).to_csv(os.path.join(OUT, "model_selection_cv.csv"))
print("\n=== STEP 6: TRAINING-ONLY CHRONOLOGICAL CV ===")
print(selection_table.round(3).to_string())
sel_name = min(
    candidate_models,
    key=lambda name: model_selection_metrics[name]["MAE"],
)
sel_pipe = candidate_models[sel_name]
sel_cv_mae = model_selection_metrics[sel_name]["MAE"]
selection_reason = (
    f"{sel_name} was selected because it had the lowest pooled MAE "
    f"({sel_cv_mae:,.2f} tonnes) across the four expanding-window training-only "
    "validation folds."
)
metric_winners = {"MAE": sel_name}
print("Selected model family:", sel_name, "| pooled CV MAE:", round(sel_cv_mae, 2))

rf.fit(X_tr, y_tr)
xgb.fit(X_tr, y_tr)
pred = {"Random Forest": np.clip(rf.predict(X_te), 0, None),
        "XGBoost": np.clip(xgb.predict(X_te), 0, None)}
res = {k: metrics(y_te, v) for k, v in pred.items()}
res["Naive baseline (Production_lag_1)"] = metrics(y_te, X_te["Production_lag_1"])
comp = pd.DataFrame(res).T
print("\n=== STEP 6: TEST METRICS (target years 2022-2024) ===")
print(comp.round(3).to_string())
comp.round(4).to_csv(os.path.join(OUT, "model_comparison.csv"))

# =============================================================================
# STEP 8 - PERFORMANCE VISUALS
# =============================================================================
test = test.assign(**{f"Pred_{k}": v for k, v in pred.items()})
top_series = (test.groupby(CAT)["Production"].sum().nlargest(4).index.tolist())
for name, p in pred.items():
    tag = name.split()[0].lower()
    # 1. Actual vs predicted scatter
    plt.figure(figsize=(6.5, 6))
    plt.scatter(y_te, p, s=14, alpha=.5, label="Predictions")
    lim = [1, max(y_te.max(), p.max()) * 1.2]
    plt.plot(lim, lim, "r--", label="Perfect prediction")
    plt.xscale("symlog"); plt.yscale("symlog")
    plt.title(f"{name}: Actual vs Predicted Production (Test 2022-2024)")
    plt.xlabel("Actual production (tonnes, symlog)"); plt.ylabel("Predicted production (tonnes, symlog)")
    plt.legend(); savefig(f"11_{tag}_actual_vs_pred_scatter")
    # 2. Actual vs predicted over time (largest 4 series)
    fig, axes = plt.subplots(2, 2, figsize=(12, 7))
    for ax, (c, f) in zip(axes.ravel(), top_series):
        h = df[(df.Country == c) & (df.Dry_Fruit == f)]
        t = test[(test.Country == c) & (test.Dry_Fruit == f)]
        ax.plot(h.Year, h.Production / 1e3, label="Actual")
        ax.plot(t.Year, t[f"Pred_{name}"] / 1e3, "o--", color="crimson", label="Predicted (test)")
        ax.axvline(TRAIN_END + .5, color="grey", ls=":"); ax.set_title(f"{c} - {f}")
        ax.set_xlabel("Year"); ax.set_ylabel("Production ('000 tonnes)"); ax.legend()
    fig.suptitle(f"{name}: Actual vs Predicted over Time (largest test series)", y=1.01); savefig(f"12_{tag}_actual_vs_pred_time")
    # 3. Residuals
    resid = y_te - p
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    ax[0].scatter(p, resid, s=12, alpha=.5, label="Residual"); ax[0].axhline(0, color="r", ls="--", label="Zero error")
    ax[0].set_xscale("symlog"); ax[0].set_yscale("symlog")
    ax[0].set_title(f"{name}: Residuals vs Predicted"); ax[0].set_xlabel("Predicted (tonnes, symlog)")
    ax[0].set_ylabel("Residual = actual - predicted (tonnes, symlog)"); ax[0].legend()
    ax[1].hist(np.clip(resid, -np.percentile(np.abs(resid), 98), np.percentile(np.abs(resid), 98)), bins=50, label="Residuals (98% range)")
    ax[1].set_title(f"{name}: Residual Distribution"); ax[1].set_xlabel("Residual (tonnes)"); ax[1].set_ylabel("Count"); ax[1].legend()
    savefig(f"13_{tag}_residuals")

def plot_importance(pipe, title, fname):
    names = pipe.named_steps["pre"].get_feature_names_out()
    imp = pd.Series(pipe.named_steps["model"].feature_importances_, index=names)
    imp.index = [i.replace("remainder__", "") for i in imp.index]
    grouped = pd.concat([imp[~imp.index.str.startswith("cat__")],
                         pd.Series({"Country (all dummies)": imp[imp.index.str.startswith("cat__Country")].sum(),
                                    "Dry_Fruit (all dummies)": imp[imp.index.str.startswith("cat__Dry_Fruit")].sum()})]
                        ).sort_values()
    plt.figure(figsize=(8, 6)); plt.barh(grouped.index, grouped.values, color="#2a7f62", label="Importance")
    plt.title(title); plt.xlabel("Feature importance"); plt.ylabel("Feature"); plt.legend(loc="lower right")
    savefig(fname); return grouped.sort_values(ascending=False)

imp_sel = plot_importance(sel_pipe, f"Feature Importance - {sel_name} (baseline)", "14_feature_importance_selected")
print("\nTop features:\n", imp_sel.head(6).round(4))

# =============================================================================
# STEP 9 - HYPERPARAMETER TUNING (expanding-window, year-based validation folds)
# =============================================================================
# The same training-only chronological folds are used for model-family selection
# and hyperparameter search. The 2022-2024 test period is not used by either step.
if sel_name == "Random Forest":
    base = RandomForestRegressor(random_state=RS, n_jobs=-1)
    space = {"model__n_estimators": [200, 300, 500], "model__max_depth": [None, 10, 20, 30],
             "model__min_samples_split": [2, 5, 10], "model__min_samples_leaf": [1, 2, 4],
             "model__max_features": ["sqrt", 0.5, 1.0]}
    n_iter = 15
else:
    base = XGBRegressor(random_state=RS, n_jobs=-1)
    space = {"model__n_estimators": [200, 400, 600], "model__max_depth": [3, 4, 6, 8],
             "model__learning_rate": [0.01, 0.03, 0.05, 0.1], "model__subsample": [0.6, 0.8, 1.0],
             "model__colsample_bytree": [0.6, 0.8, 1.0]}
    n_iter = 25
search = RandomizedSearchCV(make_pipe(base), space, n_iter=n_iter, cv=folds,
                            scoring="neg_mean_absolute_error", random_state=RS, n_jobs=1, refit=True)
search.fit(X_tr, y_tr)
tuned = search.best_estimator_
p_tuned = np.clip(tuned.predict(X_te), 0, None)
best_cv_index = int(search.best_index_)
tuning_fold_results = [
    {
        "validationYears": [
            int(train.loc[validation_indices, "Year"].min()),
            int(train.loc[validation_indices, "Year"].max()),
        ],
        "trainingRows": int(len(training_indices)),
        "validationRows": int(len(validation_indices)),
        "maeTonnes": float(-search.cv_results_[f"split{fold_index}_test_score"][best_cv_index]),
    }
    for fold_index, (training_indices, validation_indices) in enumerate(folds)
]
tune_tbl = pd.DataFrame({f"{sel_name} baseline": metrics(y_te, pred[sel_name]),
                         f"{sel_name} tuned": metrics(y_te, p_tuned)}).T
print("\n=== STEP 9: TUNING ===")
print("Best params:", search.best_params_, "| CV MAE:", round(-search.best_score_, 1))
print(tune_tbl.round(3).to_string()); tune_tbl.round(4).to_csv(os.path.join(OUT, "tuning_comparison.csv"))
naive_absolute_error = np.abs(y_te.to_numpy() - test["Production_lag_1"].to_numpy())
tuned_absolute_error = np.abs(y_te.to_numpy() - p_tuned)
paired_error_difference = tuned_absolute_error - naive_absolute_error
paired_error_frame = pd.DataFrame({
    "Country": test["Country"].to_numpy(),
    "Dry_Fruit": test["Dry_Fruit"].to_numpy(),
    "difference": paired_error_difference,
})
series_error_sums = paired_error_frame.groupby(CAT)["difference"].agg(["sum", "count"])
series_count = len(series_error_sums)
if series_count < 2:
    raise ValueError("Clustered paired inference requires at least two country-item series.")
paired_error_mean = float(np.mean(paired_error_difference))
cluster_centered_sums = (
    series_error_sums["sum"].to_numpy()
    - series_error_sums["count"].to_numpy() * paired_error_mean
)
hypothesis_difference_se = float(
    np.sqrt(
        (series_count / (series_count - 1))
        * np.sum(cluster_centered_sums**2)
    )
    / len(paired_error_difference)
)
hypothesis_degrees_of_freedom = series_count - 1
hypothesis_statistic = paired_error_mean / hypothesis_difference_se
hypothesis_p_value = float(
    student_t.cdf(hypothesis_statistic, df=hypothesis_degrees_of_freedom)
)
hypothesis_ci_critical = float(
    student_t.ppf(0.975, df=hypothesis_degrees_of_freedom)
)
hypothesis_test = {
    "name": "Tuned model vs previous-year baseline absolute errors",
    "nullHypothesis": "The tuned model's mean absolute error is greater than or equal to the previous-year baseline's.",
    "alternativeHypothesis": "The tuned model's mean absolute error is lower than the previous-year baseline's.",
    "comparison": "tuned absolute error minus previous-year baseline absolute error",
    "method": "One-sided paired comparison with country-item series-clustered standard errors",
    "sampleSize": int(len(y_te)),
    "clusterCount": int(series_count),
    "degreesOfFreedom": int(hypothesis_degrees_of_freedom),
    "statistic": float(hypothesis_statistic),
    "pValue": hypothesis_p_value,
    "alpha": 0.05,
    "meanPairedDifferenceTonnes": paired_error_mean,
    "standardDeviationPairedDifferenceTonnes": float(np.std(paired_error_difference, ddof=1)),
    "meanDifferenceCi95LowerTonnes": float(
        np.mean(paired_error_difference) - hypothesis_ci_critical * hypothesis_difference_se
    ),
    "meanDifferenceCi95UpperTonnes": float(
        np.mean(paired_error_difference) + hypothesis_ci_critical * hypothesis_difference_se
    ),
    "tunedLowerErrorCount": int(np.sum(tuned_absolute_error < naive_absolute_error)),
    "baselineLowerErrorCount": int(np.sum(tuned_absolute_error > naive_absolute_error)),
    "tieCount": int(np.sum(tuned_absolute_error == naive_absolute_error)),
    "decision": "reject_null" if hypothesis_p_value < 0.05 else "fail_to_reject_null",
}
print(
    "Series-clustered paired test (tuned < naive mean absolute error):",
    f"n={hypothesis_test['sampleSize']}, clusters={hypothesis_test['clusterCount']}, "
    f"t({hypothesis_test['degreesOfFreedom']})="
    f"{hypothesis_test['statistic']:.3f}, p={hypothesis_test['pValue']:.4f},",
    f"mean paired difference={hypothesis_test['meanPairedDifferenceTonnes']:.1f} tonnes",
)
plot_importance(tuned, f"Feature Importance - {sel_name} (tuned)", "15_feature_importance_tuned")

# Final deployable model: tuned hyper-parameters, refit on ALL labelled rows (<=LAST)
final_model = make_pipe(base.set_params(**{k.replace("model__", ""): v for k, v in search.best_params_.items()}))
final_model.fit(model_df[FEATURES], model_df["Production"])
joblib.dump(final_model, os.path.join(OUT, "final_model.joblib"))

# =============================================================================
# STEP 10 - PREDICTION FUNCTION
# =============================================================================
lookup = grid.set_index(["Country", "Dry_Fruit", "Year"])
def predict_production(country, dry_fruit, year):
    """Predict production (tonnes). Needs actual Production/Area/Yield for year-1..year-3."""
    key = (country, dry_fruit, year)
    if year > LAST + 1:
        return f"Cannot predict {year}: latest data is {LAST}, so only years up to {LAST+1} have real lag inputs."
    if key not in lookup.index:
        return f"No series for {country} / {dry_fruit} in the dataset."
    row = lookup.loc[key]
    if row[LAGS].isna().any():
        return f"Cannot predict: missing history for {country} / {dry_fruit} in {year-3}-{year-1}."
    X = pd.DataFrame([{"Country": country, "Dry_Fruit": dry_fruit, **row[LAGS].to_dict()}])[FEATURES]
    out = max(0.0, float(final_model.predict(X)[0]))
    note = f" (actual recorded: {row['Production']:,.0f} t)" if pd.notna(row["Production"]) else ""
    return f"Country: {country} | Dry fruit: {dry_fruit} | Year: {year}\nPredicted production = {out:,.0f} tonnes{note}"

print("\n=== STEP 10: EXAMPLE PREDICTIONS ===")
for c, f, y in [("India", "Almonds", 2025), ("India", "Cashew nuts", 2025),
                ("USA", "Almonds", 2025), ("Türkiye", "Hazelnuts", 2025), ("USA", "Almonds", 2027)]:
    print(predict_production(c, f, y), "\n")

# Forecast table for all series with sufficient history
fc = forecast_df[CAT + LAGS].copy()
fc["Year"] = LAST + 1
fc["Predicted_Production"] = np.clip(final_model.predict(fc[FEATURES]), 0, None)
fc = fc[["Country", "Dry_Fruit", "Year", "Predicted_Production"]]

# =============================================================================
# STEP 11 - POWER BI EXPORTS
# =============================================================================
test_out = test.copy()
test_out["Predicted_Tuned"] = p_tuned
test_out.to_csv(os.path.join(OUT, "powerbi_test_predictions.csv"), index=False)
fc.to_csv(os.path.join(OUT, f"powerbi_forecast_{LAST+1}.csv"), index=False)
kpi = {"Total_Production_t": float(df.Production.sum()), "Countries": int(df.Country.nunique()),
       "Dry_Fruits": int(df.Dry_Fruit.nunique()), "Top_Country": tot_c.index[0], "Top_Dry_Fruit": tot_f.index[0],
       "Avg_Yield_kg_ha": float(df.loc[df.Yield > 0, "Yield"].mean()),
       f"Global_Growth_{LAST-1}_to_{LAST}_%": float((g.iloc[-1] / g.iloc[-2] - 1) * 100)}

trend_years = g.index.to_numpy(dtype=float)
trend_values = g.to_numpy(dtype=float)
trend_design = np.column_stack([
    np.ones(len(trend_years)),
    (trend_years - trend_years.mean()) / 10,
])
trend_coefficients = np.linalg.lstsq(trend_design, trend_values, rcond=None)[0]
trend_residuals = trend_values - trend_design @ trend_coefficients
trend_sample_size, trend_parameter_count = trend_design.shape
trend_degrees_of_freedom = trend_sample_size - trend_parameter_count
trend_hac_lag = max(
    1,
    int(np.floor(4 * (trend_sample_size / 100) ** (2 / 9))),
)
trend_weighted_residuals = trend_design * trend_residuals[:, None]
trend_hac_meat = trend_weighted_residuals.T @ trend_weighted_residuals
for lag in range(1, trend_hac_lag + 1):
    lag_weight = 1 - lag / (trend_hac_lag + 1)
    lagged_covariance = trend_weighted_residuals[lag:].T @ trend_weighted_residuals[:-lag]
    trend_hac_meat += lag_weight * (lagged_covariance + lagged_covariance.T)
trend_design_inverse = np.linalg.inv(trend_design.T @ trend_design)
trend_hac_covariance = (
    trend_design_inverse
    @ trend_hac_meat
    @ trend_design_inverse
    * (trend_sample_size / trend_degrees_of_freedom)
)
trend_slope_standard_error = float(np.sqrt(trend_hac_covariance[1, 1]))
trend_statistic = float(trend_coefficients[1] / trend_slope_standard_error)
trend_p_value = float(student_t.sf(trend_statistic, trend_degrees_of_freedom))
production_trend_test = {
    "name": "Positive linear trend in annual global production",
    "nullHypothesis": "Annual global production has no positive linear trend (slope <= 0).",
    "alternativeHypothesis": "Annual global production has a positive linear trend (slope > 0).",
    "method": "One-sided OLS trend t-test with Newey-West HAC standard errors",
    "sampleSize": int(trend_sample_size),
    "degreesOfFreedom": int(trend_degrees_of_freedom),
    "hacLag": int(trend_hac_lag),
    "startYear": int(trend_years.min()),
    "endYear": int(trend_years.max()),
    "slopeMillionTonnesPerDecade": float(trend_coefficients[1]),
    "slopeStandardErrorMillionTonnesPerDecade": trend_slope_standard_error,
    "statistic": trend_statistic,
    "pValue": trend_p_value,
    "alpha": 0.05,
    "decision": "reject_null" if trend_p_value < 0.05 else "fail_to_reject_null",
}
print(
    "Global production trend (one-sided HAC t-test):",
    f"slope={production_trend_test['slopeMillionTonnesPerDecade']:.3f} million tonnes/decade,",
    f"t({trend_degrees_of_freedom})={trend_statistic:.3f}, p={trend_p_value:.4g}",
)
with open(os.path.join(OUT, "dashboard_kpis.json"), "w", encoding="utf-8") as output_file:
    json.dump(kpi, output_file, indent=2)

dashboard_data = {
    "kpis": kpi,
    "yearRange": [int(df["Year"].min()), int(LAST)],
    "cleanRows": int(len(df)),
    "modelReadyRows": int(len(model_df)),
    "trainingRows": int(len(train)),
    "testRows": int(len(test)),
    "selectedModel": sel_name,
    "selectionReason": selection_reason,
    "selectionMetricWinners": metric_winners,
    "modelSelectionValidation": {
        "method": "Pooled MAE across expanding-window chronological folds using training data only",
        "selectedMetric": "MAE",
        "selectedModel": sel_name,
        "models": [
            {
                "model": model,
                **{metric: float(value) for metric, value in values.items()},
            }
            for model, values in model_selection_metrics.items()
        ],
    },
    "tuningValidation": {
        "method": "Expanding-window cross-validation scored by MAE",
        "bestMeanAbsoluteError": float(-search.best_score_),
        "folds": [
            {
                "trainingThrough": int(fold["validationYears"][0] - 1),
                **fold,
            }
            for fold in tuning_fold_results
        ],
    },
    "hypothesisTest": hypothesis_test,
    "yearlyHoldoutMetrics": [
        {
            "year": int(year),
            "rows": int(len(year_rows)),
            "tuned": {
                metric: float(value)
                for metric, value in metrics(
                    year_rows["Production"],
                    year_rows["Predicted_Tuned"],
                ).items()
            },
            "previousYearBaseline": {
                metric: float(value)
                for metric, value in metrics(
                    year_rows["Production"],
                    year_rows["Production_lag_1"],
                ).items()
            },
        }
        for year, year_rows in test_out.groupby("Year", sort=True)
    ],
    "productionTrendTest": production_trend_test,
    "forecast": fc.to_dict(orient="records"),
    "annualProduction": [
        {"year": int(year), "production_tonnes": float(value * 1e6)}
        for year, value in g.items()
    ],
    "fruitProduction": [
        {"dry_fruit": item, "production_tonnes": float(value)}
        for item, value in tot_f.items()
    ],
    "countryProduction": [
        {"country": country, "production_tonnes": float(value)}
        for country, value in tot_c.head(10).items()
    ],
    "mapData": [
        {
            "country": country,
            "dry_fruit": dry_fruit,
            "year": int(year),
            "production_tonnes": float(production),
        }
        for (country, dry_fruit, year), production in (
            df.groupby(["Country", "Dry_Fruit", "Year"])["Production"].sum().items()
        )
    ],
    "correlation": {
        "labels": corr.columns.tolist(),
        "values": corr.round(3).values.tolist(),
    },
    "modelMetrics": [
        {"model": model, **{metric: float(value) for metric, value in values.items()}}
        for model, values in res.items()
    ],
    "tuningMetrics": [
        {"model": model, **{metric: float(value) for metric, value in values.items()}}
        for model, values in tune_tbl.to_dict(orient="index").items()
    ],
}
dashboard_data_js = "window.DRY_FRUIT_DASHBOARD_DATA = " + json.dumps(
    dashboard_data, ensure_ascii=False, allow_nan=False, separators=(",", ":")
) + ";\n"
with open(os.path.join(OUT, "dashboard_data.js"), "w", encoding="utf-8") as output_file:
    output_file.write(dashboard_data_js)
print("\n=== STEP 11: KPIs ===\n", json.dumps(kpi, indent=2))
print("\nDone. Files in", OUT)

# Zip everything (data, figures, model) and download it from Colab
if IN_COLAB:
    import shutil
    shutil.make_archive("/content/dry_fruits_outputs", "zip", OUT)
    files.download("/content/dry_fruits_outputs.zip")
