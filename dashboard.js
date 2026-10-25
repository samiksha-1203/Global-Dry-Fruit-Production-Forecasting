(() => {
  "use strict";

  const data = window.DRY_FRUIT_DASHBOARD_DATA;
  const status = document.getElementById("dashboard-status");
  if (!data) {
    status.textContent = "Dashboard data is missing. Rerun dry_fruits_production_analysis.py.";
    return;
  }

  const formatNumber = (value, digits = 0) =>
    Number(value).toLocaleString(undefined, {
      maximumFractionDigits: digits,
      minimumFractionDigits: digits,
    });
  const formatTonnes = (value) => `${formatNumber(value)} tonnes`;
  const plotConfig = { responsive: true, displaylogo: false };
  const previousCountryColors = {
    "Afghanistan": "#AA0DFE",
    "Albania": "#3283FE",
    "Algeria": "#85660D",
    "Angola": "#782AB6",
    "Argentina": "#565656",
    "Armenia": "#1C8356",
    "Australia": "#16FF32",
    "Austria": "#F7E1A0",
    "Azerbaijan": "#E2E2E2",
    "Bahrain": "#1CBE4F",
    "Belarus": "#C4451C",
    "Belgium": "#DEA0FD",
    "Belize": "#FE00FA",
    "Benin": "#325A9B",
    "Bhutan": "#FEAF16",
    "Bolivia": "#F8A19F",
    "Bosnia and Herzegovina": "#90AD1C",
    "Brazil": "#F6222E",
    "Bulgaria": "#1CFFCE",
    "Burkina Faso": "#2ED9FF",
    "Cameroon": "#B10DA1",
    "Chad": "#C075A6",
    "Chile": "#FC1CBF",
    "China": "#B00068",
    "Colombia": "#FBE426",
    "Comoros": "#FA0087",
    "Croatia": "#2E91E5",
    "Cyprus": "#E15F99",
    "Czech Republic": "#1CA71C",
    "Côte d'Ivoire": "#FB0D0D",
    "Denmark": "#DA16FF",
    "Djibouti": "#222A2A",
    "Dominican Republic": "#B68100",
    "Ecuador": "#750D86",
    "Egypt": "#EB663B",
    "El Salvador": "#511CFB",
    "Estonia": "#00A08B",
    "Eswatini": "#FB00D1",
    "Finland": "#FC0080",
    "France": "#B2828D",
    "Gambia": "#6C7C32",
    "Georgia": "#778AAE",
    "Germany": "#862A16",
    "Ghana": "#A777F1",
    "Greece": "#620042",
    "Guinea": "#1616A7",
    "Guinea-Bissau": "#DA60CA",
    "Honduras": "#6C4516",
    "Hungary": "#0D2A63",
    "India": "#AF0038",
    "Indonesia": "#FD3216",
    "Iran": "#00FE35",
    "Iraq": "#6A76FC",
    "Ireland": "#FED4C4",
    "Israel": "#FE00CE",
    "Italy": "#0DF9FF",
    "Japan": "#F6F926",
    "Jordan": "#FF9616",
    "Kazakhstan": "#479B55",
    "Kenya": "#EEA6FB",
    "Kuwait": "#DC587D",
    "Kyrgyzstan": "#D626FF",
    "Latvia": "#6E899C",
    "Lebanon": "#00B5F7",
    "Libya": "#B68E00",
    "Lithuania": "#C9FBE5",
    "Luxembourg": "#FF0092",
    "Madagascar": "#22FFA7",
    "Malawi": "#E3EE9E",
    "Malaysia": "#86CE00",
    "Mali": "#BC7196",
    "Malta": "#7E7DCD",
    "Mauritania": "#FC6955",
    "Mauritius": "#E48F72",
    "Mexico": "#AA0DFE",
    "Moldova": "#3283FE",
    "Mongolia": "#85660D",
    "Montenegro": "#782AB6",
    "Morocco": "#565656",
    "Mozambique": "#1C8356",
    "Myanmar": "#16FF32",
    "Namibia": "#F7E1A0",
    "Nepal": "#E2E2E2",
    "Netherlands": "#1CBE4F",
    "New Zealand": "#C4451C",
    "Niger": "#DEA0FD",
    "Nigeria": "#FE00FA",
    "North Korea": "#325A9B",
    "North Macedonia": "#FEAF16",
    "Oman": "#F8A19F",
    "Pakistan": "#90AD1C",
    "Palestine": "#F6222E",
    "Peru": "#1CFFCE",
    "Philippines": "#2ED9FF",
    "Poland": "#B10DA1",
    "Portugal": "#C075A6",
    "Qatar": "#FC1CBF",
    "Romania": "#B00068",
    "Saudi Arabia": "#FBE426",
    "Senegal": "#FA0087",
    "Serbia": "#2E91E5",
    "Serbia and Montenegro": "#E15F99",
    "Sierra Leone": "#1CA71C",
    "Slovakia": "#FB0D0D",
    "Slovenia": "#DA16FF",
    "Somalia": "#222A2A",
    "South Africa": "#B68100",
    "South Korea": "#750D86",
    "Spain": "#EB663B",
    "Sri Lanka": "#511CFB",
    "Sudan": "#00A08B",
    "Sudan (former)": "#FB00D1",
    "Sweden": "#FC0080",
    "Switzerland": "#B2828D",
    "Syria": "#6C7C32",
    "Tajikistan": "#778AAE",
    "Tanzania": "#862A16",
    "Thailand": "#A777F1",
    "Togo": "#620042",
    "Tunisia": "#1616A7",
    "Turkmenistan": "#DA60CA",
    "Turkey": "#6C4516",
    "USA": "#0D2A63",
    "Ukraine": "#AF0038",
    "United Arab Emirates": "#FD3216",
    "Uzbekistan": "#00FE35",
    "Vietnam": "#6A76FC",
    "Yemen": "#FED4C4",
    "Zimbabwe": "#FE00CE",
  };
  const cropPalette = {
    Almonds: "#FB8072",
    "Brazil nuts": "#D9D9D9",
    "Cashew nuts": "#FFFFB3",
    Chestnuts: "#80B1D3",
    Dates: "#8DD3C7",
    Figs: "#FDB462",
    Hazelnuts: "#B3DE69",
    Pistachios: "#FCCDE5",
    Walnuts: "#BEBADA",
  };
  const forecastPalette = {
    "Hazelnuts": "rgb(102, 197, 204)",
    "Cashew nuts": "rgb(246, 207, 113)",
    "Dates": "rgb(248, 156, 116)",
    "Chestnuts": "rgb(220, 176, 242)",
    "Walnuts": "rgb(135, 197, 95)",
    "Almonds": "rgb(158, 185, 243)",
  };
  const modelPalette = {
    "Random Forest": "rgb(127, 60, 141)",
    "XGBoost": "rgb(17, 165, 121)",
    "Naive baseline (Production_lag_1)": "rgb(57, 105, 172)",
  };

  function renderPlot(id, traces, layout) {
    const target = document.getElementById(id);
    if (!target || !window.Plotly) return;
    const chartLayout = {
      ...layout,
      title: typeof layout.title === "string" ? { text: layout.title } : layout.title,
    };
    Plotly.newPlot(target, traces, {
      paper_bgcolor: "white",
      plot_bgcolor: "#E5ECF6",
      font: { color: "#2a3f5f" },
      margin: { t: 28, r: 24, b: 55, l: 80 },
      ...chartLayout,
    }, plotConfig);
  }

  const [firstYear, lastYear] = data.yearRange;
  const yearPeriod = `${firstYear}–${lastYear}`;
  document.getElementById("dashboard-status").textContent =
    `Current pipeline output · ${data.cleanRows.toLocaleString()} cleaned rows · ${yearPeriod}`;
  if (!window.Plotly) {
    document.getElementById("dashboard-status").textContent +=
      " · Charts unavailable: check your internet connection and reload.";
  }
  document.getElementById("kpi-production").textContent =
    `${(data.kpis.Total_Production_t / 1e6).toFixed(1)}M`;
  document.getElementById("kpi-countries").textContent = data.kpis.Countries;
  document.getElementById("kpi-items").textContent = data.kpis.Dry_Fruits;
  document.getElementById("kpi-top-country").textContent = data.kpis.Top_Country;
  document.getElementById("kpi-top-fruit").textContent = data.kpis.Top_Dry_Fruit;
  document.getElementById("kpi-growth").textContent =
    `${data.kpis[`Global_Growth_${lastYear - 1}_to_${lastYear}_%`].toFixed(2)}%`;
  document.getElementById("production-period").textContent =
    `Cumulative production, ${yearPeriod} (million tonnes)`;
  document.getElementById("analysis-summary").textContent =
    `${data.cleanRows.toLocaleString()} cleaned country-item-year rows across ${data.kpis.Countries} countries/areas and ${data.kpis.Dry_Fruits} selected crop items.`;
  document.getElementById("clean-row-count").textContent = data.cleanRows.toLocaleString();
  document.getElementById("year-period").textContent = yearPeriod;
  document.getElementById("forecast-count").textContent = data.forecast.length.toLocaleString();
  document.getElementById("model-summary").textContent =
    `Training-only chronological validation uses ${data.trainingRows.toLocaleString()} rows through 2021 to select and tune the model; the final holdout contains ${data.testRows.toLocaleString()} rows from 2022–${lastYear}.`;
  document.getElementById("selected-model").textContent = data.selectedModel;
  document.getElementById("selection-reason").textContent = data.selectionReason;
  const selectionValidation = data.modelSelectionValidation;
  const selectionColumns = [
    ["MAE", "MAE (tonnes)", (value) => formatNumber(value)],
    ["RMSE", "RMSE (tonnes)", (value) => formatNumber(value)],
    ["R2", "R²", (value) => Number(value).toFixed(4)],
    ["MAPE_%", "MAPE", (value) => `${Number(value).toFixed(2)}%`],
    ["WAPE_%", "WAPE", (value) => `${Number(value).toFixed(2)}%`],
  ];
  document.getElementById("model-selection-table").innerHTML =
    `<table><thead><tr><th>Model family / reference</th>${selectionColumns.map(([, label]) => `<th>${label}</th>`).join("")}</tr></thead><tbody>${selectionValidation.models.map((row) => `<tr${row.model === selectionValidation.selectedModel ? ' class="selected-model-row"' : ""}><th>${row.model}${row.model === selectionValidation.selectedModel ? " (selected)" : ""}</th>${selectionColumns.map(([key, , format]) => `<td>${format(row[key])}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  const validation = data.tuningValidation;
  const validationFolds = validation.folds
    .map((fold) => `${fold.validationYears[0]}–${fold.validationYears[1]}`)
    .join(", ");
  document.getElementById("validation-summary").textContent =
    `${validation.method} used ${validation.folds.length} chronological folds (${validationFolds}); best mean validation MAE was ${formatNumber(validation.bestMeanAbsoluteError)} tonnes. Model-family selection and tuning did not use the final 2022–${lastYear} holdout.`;
  const cvFoldTable = document.getElementById("cv-fold-table");
  cvFoldTable.innerHTML = `<table><thead><tr><th>Training through</th><th>Training rows</th><th>Validation years</th><th>Validation rows</th><th>MAE (tonnes)</th></tr></thead><tbody>${validation.folds.map((fold) => `<tr><td>${fold.trainingThrough}</td><td>${formatNumber(fold.trainingRows)}</td><td>${fold.validationYears[0]}–${fold.validationYears[1]}</td><td>${formatNumber(fold.validationRows)}</td><td>${formatNumber(fold.maeTonnes)}</td></tr>`).join("")}</tbody></table>`;
  const yearlyMetrics = data.yearlyHoldoutMetrics;
  const yearlyValidationTable = document.getElementById("yearly-validation-table");
  yearlyValidationTable.innerHTML = `<table><thead><tr><th>Test year</th><th>Rows</th><th>Tuned MAE</th><th>Baseline MAE</th><th>Tuned RMSE</th><th>Baseline RMSE</th><th>Tuned WAPE</th><th>Baseline WAPE</th></tr></thead><tbody>${yearlyMetrics.map((row) => `<tr><th>${row.year}</th><td>${formatNumber(row.rows)}</td><td>${formatNumber(row.tuned.MAE)}</td><td>${formatNumber(row.previousYearBaseline.MAE)}</td><td>${formatNumber(row.tuned.RMSE)}</td><td>${formatNumber(row.previousYearBaseline.RMSE)}</td><td>${Number(row.tuned["WAPE_%"]).toFixed(2)}%</td><td>${Number(row.previousYearBaseline["WAPE_%"]).toFixed(2)}%</td></tr>`).join("")}</tbody></table>`;
  const hypothesis = data.hypothesisTest;
  document.getElementById("hypothesis-null").textContent = hypothesis.nullHypothesis;
  document.getElementById("hypothesis-alternative").textContent = hypothesis.alternativeHypothesis;
  document.getElementById("hypothesis-method").textContent =
    `${hypothesis.method} · α = ${hypothesis.alpha.toFixed(2)} · ${hypothesis.sampleSize.toLocaleString()} paired held-out predictions across ${hypothesis.clusterCount.toLocaleString()} country-item series · df = ${hypothesis.degreesOfFreedom.toLocaleString()}.`;
  document.getElementById("hypothesis-statistics").textContent =
    `t(${hypothesis.degreesOfFreedom.toLocaleString()}) = ${hypothesis.statistic.toFixed(3)}; one-sided p-value = ${hypothesis.pValue < 0.001 ? hypothesis.pValue.toExponential(2) : hypothesis.pValue.toFixed(4)}; mean paired absolute-error difference (tuned − previous-year baseline) = ${formatNumber(hypothesis.meanPairedDifferenceTonnes)} tonnes (SD ${formatNumber(hypothesis.standardDeviationPairedDifferenceTonnes)} tonnes); 95% CI for the mean difference = [${formatNumber(hypothesis.meanDifferenceCi95LowerTonnes)}, ${formatNumber(hypothesis.meanDifferenceCi95UpperTonnes)}] tonnes. Tuned model has lower absolute error in ${hypothesis.tunedLowerErrorCount.toLocaleString()} cases; baseline has lower error in ${hypothesis.baselineLowerErrorCount.toLocaleString()}${hypothesis.tieCount ? `; tied in ${hypothesis.tieCount.toLocaleString()}` : ""}.`;
  document.getElementById("hypothesis-conclusion").textContent =
    hypothesis.decision === "reject_null"
      ? `Reject H₀ at α = ${hypothesis.alpha.toFixed(2)}: the test supports lower paired absolute errors for the tuned model.`
      : `Fail to reject H₀ at α = ${hypothesis.alpha.toFixed(2)}: the test does not support the claim that the tuned model has lower paired absolute errors.`;
  const ciIncludesZero =
    hypothesis.meanDifferenceCi95LowerTonnes <= 0 &&
    hypothesis.meanDifferenceCi95UpperTonnes >= 0;
  renderPlot("model-hypothesis-chart", [{
    type: "scatter",
    mode: "markers",
    x: [hypothesis.meanPairedDifferenceTonnes],
    y: ["Mean paired error difference"],
    marker: { color: ciIncludesZero ? "#E39A32" : "#23966A", size: 14 },
    error_x: {
      type: "data",
      symmetric: false,
      array: [
        hypothesis.meanDifferenceCi95UpperTonnes -
          hypothesis.meanPairedDifferenceTonnes,
      ],
      arrayminus: [
        hypothesis.meanPairedDifferenceTonnes -
          hypothesis.meanDifferenceCi95LowerTonnes,
      ],
      color: "#754C24",
      thickness: 2,
      width: 8,
    },
    hovertemplate: "Mean difference: %{x:,.0f} tonnes<extra></extra>",
  }], {
    title: "Model hypothesis: paired error difference (95% CI)",
    xaxis: { title: "Tuned − baseline absolute error (tonnes)", zeroline: false },
    yaxis: { automargin: true },
    shapes: [{
      type: "line",
      x0: 0,
      x1: 0,
      y0: 0,
      y1: 1,
      xref: "x",
      yref: "paper",
      line: { color: "#B83B32", width: 2, dash: "dash" },
    }],
    annotations: [{
      x: 0,
      y: 0.48,
      xref: "x",
      yref: "paper",
      text: "Zero difference",
      showarrow: false,
      font: { color: "#B83B32", size: 11 },
    }],
    margin: { l: 155, r: 30, t: 55, b: 65 },
  });
  const trendTest = data.productionTrendTest;
  document.getElementById("trend-null").textContent = trendTest.nullHypothesis;
  document.getElementById("trend-alternative").textContent = trendTest.alternativeHypothesis;
  document.getElementById("trend-method").textContent =
    `${trendTest.method} · one-sided · α = ${trendTest.alpha.toFixed(2)} · ${trendTest.sampleSize} annual observations (${trendTest.startYear}–${trendTest.endYear}) · HAC lag = ${trendTest.hacLag}.`;
  document.getElementById("trend-statistics").textContent =
    `Estimated trend: +${trendTest.slopeMillionTonnesPerDecade.toFixed(2)} million tonnes per decade (HAC SE ${trendTest.slopeStandardErrorMillionTonnesPerDecade.toFixed(2)}); t(${trendTest.degreesOfFreedom}) = ${trendTest.statistic.toFixed(2)}; p-value = ${trendTest.pValue < 0.001 ? trendTest.pValue.toExponential(2) : trendTest.pValue.toFixed(4)}.`;
  document.getElementById("trend-conclusion").textContent =
    trendTest.decision === "reject_null"
      ? `Reject H₀ at α = ${trendTest.alpha.toFixed(2)}: this dataset provides statistically significant evidence of a positive linear production trend.`
      : `Fail to reject H₀ at α = ${trendTest.alpha.toFixed(2)}: this dataset does not provide statistically significant evidence of a positive linear production trend.`;
  const annualMeanProduction =
    data.annualProduction.reduce((total, row) => total + row.production_tonnes, 0) /
    data.annualProduction.length;
  const annualMeanYear =
    data.annualProduction.reduce((total, row) => total + row.year, 0) /
    data.annualProduction.length;
  const fittedTrend = data.annualProduction.map((row) => ({
    year: row.year,
    production_tonnes:
      annualMeanProduction +
      trendTest.slopeMillionTonnesPerDecade *
        1e6 *
        ((row.year - annualMeanYear) / 10),
  }));
  renderPlot("trend-hypothesis-chart", [
    {
      type: "scatter",
      mode: "lines+markers",
      name: "Observed annual production",
      x: data.annualProduction.map((row) => row.year),
      y: data.annualProduction.map((row) => row.production_tonnes),
      line: { color: "#636efa", width: 3 },
      marker: { size: 6 },
      hovertemplate: "%{x}: %{y:.3s} tonnes<extra></extra>",
    },
    {
      type: "scatter",
      mode: "lines",
      name: "Fitted linear trend",
      x: fittedTrend.map((row) => row.year),
      y: fittedTrend.map((row) => row.production_tonnes),
      line: { color: "#E39A32", width: 3, dash: "dash" },
      hovertemplate: "%{x}: %{y:.3s} tonnes<extra></extra>",
    },
  ], {
    title: "Production trend hypothesis: observed data and fitted line",
    xaxis: {
      title: "Year",
      tickvals: data.annualProduction
        .filter((row) => row.year % 5 === 0)
        .map((row) => row.year),
      tickformat: "d",
      tickangle: -25,
      automargin: true,
    },
    yaxis: {
      title: "Annual production (tonnes)",
      tickformat: ".2s",
      separatethousands: true,
      exponentformat: "none",
      showexponent: "none",
    },
    legend: { orientation: "h", y: -0.25 },
  });
  document.getElementById("forecast-summary").textContent =
    `${data.forecast.length} model-generated country/item forecasts for 2025. These are estimates, not observed production.`;

  renderPlot("yearly-chart", [{
    type: "scatter",
    mode: "lines+markers",
    x: data.annualProduction.map((row) => row.year),
    y: data.annualProduction.map((row) => row.production_tonnes),
    line: { color: "#636efa", width: 3 },
    marker: { size: 7 },
    hovertemplate: "%{x}: %{y:.3s} tonnes<extra></extra>",
    name: "Production",
  }], {
    title: "Annual production",
    xaxis: { title: "Year", tickvals: data.annualProduction.filter((row) => row.year % 5 === 0).map((row) => row.year), tickformat: "d", tickangle: -25, automargin: true },
    yaxis: { title: "Production (tonnes)", tickformat: ".2s", separatethousands: true, exponentformat: "none", showexponent: "none" },
  });

  const annualGrowth = data.annualProduction.slice(1).map((row, index) => {
    const previous = data.annualProduction[index];
    return {
      year: row.year,
      growth_percent: ((row.production_tonnes - previous.production_tonnes) /
        previous.production_tonnes) * 100,
      previous_production: previous.production_tonnes,
      production: row.production_tonnes,
    };
  });
  renderPlot("growth-chart", [{
    type: "bar",
    x: annualGrowth.map((row) => row.year),
    y: annualGrowth.map((row) => row.growth_percent),
    customdata: annualGrowth.map((row) => [row.previous_production, row.production]),
    marker: {
      color: annualGrowth.map((row) => row.growth_percent >= 0 ? "#00CC96" : "#EF553B"),
    },
    hovertemplate: "%{x}: %{y:+.2f}%<br>Previous year: %{customdata[0]:,.0f} tonnes<br>This year: %{customdata[1]:,.0f} tonnes<extra></extra>",
    name: "Year-over-year change",
  }], {
    title: "Year-over-year production growth",
    xaxis: { title: "Year", tickvals: annualGrowth.filter((row) => row.year % 5 === 0).map((row) => row.year), tickformat: "d", tickangle: -25, automargin: true },
    yaxis: { title: "Change from previous year (%)", ticksuffix: "%", zeroline: true, zerolinecolor: "#2a3f5f", zerolinewidth: 1.5 },
  });

  renderPlot("fruit-chart", [{
    type: "pie",
    labels: data.fruitProduction.map((row) => row.dry_fruit),
    values: data.fruitProduction.map((row) => row.production_tonnes),
    hole: 0.48,
    sort: false,
    marker: {
      colors: data.fruitProduction.map((row) => cropPalette[row.dry_fruit]),
      line: { color: "white", width: 2 },
    },
    textinfo: "percent",
    textposition: "outside",
    hovertemplate: "%{label}<br>Production: %{value:,.0f} tonnes<extra></extra>",
  }], {
    title: `Cumulative production by crop (${yearPeriod})`,
    plot_bgcolor: "white",
    showlegend: true,
    legend: { orientation: "v", x: 1.02, y: 0.5 },
    margin: { l: 15, r: 120, t: 45, b: 20 },
  });

  const countryCropTotals = new Map();
  for (const row of data.mapData) {
    if (!countryCropTotals.has(row.country)) countryCropTotals.set(row.country, new Map());
    const totals = countryCropTotals.get(row.country);
    totals.set(row.dry_fruit, (totals.get(row.dry_fruit) || 0) + row.production_tonnes);
  }
  const countryLeadingCrop = (country) => {
    const totals = countryCropTotals.get(country);
    return totals
      ? [...totals.entries()].sort((a, b) => b[1] - a[1])[0]?.[0]
      : undefined;
  };
  const mapCountryNames = {
    "China (mainland)": "China",
    "Côte d'Ivoire": "Ivory Coast",
    Czechia: "Czech Republic",
    "North Korea": "North Korea",
    "South Korea": "South Korea",
    Taiwan: "Taiwan",
    Türkiye: "Turkey",
    UK: "United Kingdom",
    USA: "United States",
    "Viet Nam": "Vietnam",
  };
  const countryColorFor = (country) =>
    previousCountryColors[country] ||
    previousCountryColors[mapCountryNames[country] || country] ||
    "#636EFA";

  renderPlot("country-chart", [{
    type: "bar",
    orientation: "h",
    x: data.countryProduction.map((row) => row.production_tonnes / 1e6),
    y: data.countryProduction.map((row) => row.country),
    customdata: data.countryProduction.map((row) => [countryLeadingCrop(row.country)]),
    marker: {
      color: data.countryProduction.map((row) => countryColorFor(row.country)),
    },
    hovertemplate: "%{y}: %{x:.2f} million tonnes<br>Leading crop: %{customdata[0]}<extra></extra>",
  }], {
    title: `Top 10 producers (${yearPeriod})`,
    xaxis: { title: "Production (million tonnes)" },
    yaxis: { autorange: "reversed" },
    margin: { l: 140, r: 24, t: 45, b: 55 },
  });

  const mapCropSelect = document.getElementById("map-crop");
  const mapYearSelect = document.getElementById("map-year");
  const mapSummary = document.getElementById("map-summary");
  const mapCrops = [...new Set(data.mapData.map((row) => row.dry_fruit))]
    .sort((a, b) => a.localeCompare(b));
  mapCropSelect.add(new Option("All crop items", "all"));
  for (const crop of mapCrops) mapCropSelect.add(new Option(crop, crop));
  mapYearSelect.add(new Option(`Cumulative (${firstYear}–${lastYear})`, "all"));
  for (let year = firstYear; year <= lastYear; year += 1) {
    mapYearSelect.add(new Option(String(year), String(year)));
  }
  mapYearSelect.value = "all";

  function updateWorldMap() {
    const selectedCrop = mapCropSelect.value;
    const selectedYear = mapYearSelect.value;
    const rows = data.mapData.filter((row) =>
      (selectedCrop === "all" || row.dry_fruit === selectedCrop) &&
      (selectedYear === "all" || row.year === Number(selectedYear))
    );
    const countries = new Map();
    for (const row of rows) {
      const current = countries.get(row.country) || {
        production: 0,
        cropTotals: new Map(),
      };
      current.production += row.production_tonnes;
      current.cropTotals.set(
        row.dry_fruit,
        (current.cropTotals.get(row.dry_fruit) || 0) + row.production_tonnes,
      );
      countries.set(row.country, current);
    }
    const entries = [...countries.entries()]
      .map(([country, item]) => {
        const leadingCrop = [...item.cropTotals.entries()]
          .sort((a, b) => b[1] - a[1])[0];
        return {
          country,
          location: mapCountryNames[country] || country,
          production: item.production,
          leadingCrop: leadingCrop?.[1] > 0 ? leadingCrop[0] : "No positive production",
          color: countryColorFor(country),
        };
      });
    const isCumulative = selectedYear === "all";
    const period = isCumulative ? yearPeriod : selectedYear;
    const cropLabel = selectedCrop === "all" ? "all selected crops" : selectedCrop;
    const mapLayout = {
      title: `${selectedCrop === "all" ? "All selected crops" : selectedCrop} production · ${period}`,
      geo: {
        scope: "world",
        projection: { type: "natural earth" },
        showframe: false,
        showcoastlines: true,
        coastlinecolor: "#c6b8a7",
        showcountries: true,
        countrycolor: "#777777",
        showland: true,
        landcolor: "#E5ECF6",
        showocean: true,
        oceancolor: "white",
        bgcolor: "white",
      },
      margin: { l: 0, r: 0, t: 48, b: 0 },
    };
    if (!entries.length) {
      renderPlot("world-map", [], mapLayout);
      mapSummary.textContent =
        `No production records are available for ${cropLabel} in ${period}.`;
      return;
    }
    const countryColors = [...new Set(entries.map((row) => row.color))];
    const countryColorIndexes = new Map(countryColors.map((color, index) => [color, index]));
    const categoryScale = countryColors.flatMap((color, index) => {
      const lower = index / countryColors.length;
      const upper = (index + 1) / countryColors.length;
      return [[lower, color], [upper, color]];
    });
    renderPlot("world-map", [{
      type: "choropleth",
      locationmode: "country names",
      locations: entries.map((row) => row.location),
      z: entries.map((row) => countryColorIndexes.get(row.color)),
      customdata: entries.map((row) => [row.country, row.production, row.leadingCrop]),
      colorscale: categoryScale,
      zmin: -0.5,
      zmax: Math.max(0.5, countryColors.length - 0.5),
      showscale: false,
      marker: { line: { color: "#777777", width: 0.55 } },
      hovertemplate: "<b>%{customdata[0]}</b><br>Production: %{customdata[1]:,.0f} tonnes<br>Leading crop: %{customdata[2]}<extra></extra>",
    }], mapLayout);
    const positiveCountries = entries.filter((row) => row.production > 0).length;
    mapSummary.textContent =
      `${entries.length} countries/areas shown (${positiveCountries} with positive production) · ${cropLabel} · ${isCumulative ? `cumulative ${period}` : `year ${period}`} · each country keeps its own vivid color; hover to see its leading crop and production in tonnes.`;
  }

  mapCropSelect.addEventListener("change", updateWorldMap);
  mapYearSelect.addEventListener("change", updateWorldMap);
  updateWorldMap();

  renderPlot("correlation-chart", [{
    type: "heatmap",
    x: data.correlation.labels,
    y: data.correlation.labels,
    z: data.correlation.values,
    zmin: -1,
    zmax: 1,
    colorscale: "RdBu",
    reversescale: true,
    text: data.correlation.values.map((row) => row.map((value) => value.toFixed(2))),
    texttemplate: "%{text}",
    hovertemplate: "%{y} vs %{x}: %{z:.3f}<extra></extra>",
    showscale: true,
  }], {
    title: "Pearson correlation (log1p-transformed variables)",
    xaxis: { automargin: true },
    yaxis: { automargin: true, autorange: "reversed" },
    margin: { l: 130, r: 30, t: 50, b: 100 },
  });

  const metricColumns = [
    ["MAE", "MAE (tonnes)", (value) => formatNumber(value)],
    ["RMSE", "RMSE (tonnes)", (value) => formatNumber(value)],
    ["R2", "R²", (value) => Number(value).toFixed(4)],
    ["MAPE_%", "MAPE", (value) => `${Number(value).toFixed(2)}%`],
    ["WAPE_%", "WAPE", (value) => `${Number(value).toFixed(2)}%`],
  ];
  const metricsTable = document.getElementById("metrics-table");
  metricsTable.innerHTML = `<table><thead><tr><th>Model</th>${metricColumns.map(([, label]) => `<th>${label}</th>`).join("")}</tr></thead><tbody>${data.modelMetrics.map((row) => `<tr><th>${row.model}</th>${metricColumns.map(([key, , format]) => `<td>${format(row[key])}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  const tunedTable = document.getElementById("tuning-table");
  tunedTable.innerHTML = `<table><thead><tr><th>Selected model</th>${metricColumns.map(([, label]) => `<th>${label}</th>`).join("")}</tr></thead><tbody>${data.tuningMetrics.map((row) => `<tr><th>${row.model}</th>${metricColumns.map(([key, , format]) => `<td>${format(row[key])}</td>`).join("")}</tr>`).join("")}</tbody></table>`;

  renderPlot("model-chart", data.modelMetrics.map((row) => ({
    type: "bar",
    name: row.model,
    x: [row.model],
    y: [row.RMSE],
    marker: { color: modelPalette[row.model] || "#636EFA" },
    text: [formatNumber(row.RMSE)],
    textposition: "outside",
    hovertemplate: "%{x}<br>RMSE: %{y:,.0f} tonnes<extra></extra>",
  })), {
    title: "Final holdout RMSE by model (lower is better)",
    yaxis: { title: "RMSE (tonnes)", rangemode: "tozero" },
    showlegend: false,
    margin: { l: 75, r: 20, t: 45, b: 75 },
  });

  const figures = [
    ["01_top_countries.png", "Top producers by country", "Cumulative production across the full historical period."],
    ["02_top_fruits.png", "Production by crop item", "Compare cumulative production across the selected crops."],
    ["03_global_trend.png", "Global production trend", "Year-by-year total production for all selected crops."],
    ["04_fruit_trends.png", "Crop production trends", "Annual crop-item trends shown on a logarithmic scale."],
    ["05_top_countries_per_fruit.png", "Leading producers by crop", "Top producing countries for each of the six largest crop items."],
    ["06_area_vs_production.png", "Harvested area and production", "Relationship between harvested area and production on log axes."],
    ["07_yield_vs_production.png", "Yield and production", "Production observations compared with yield on log axes."],
    ["08_correlation_heatmap.png", "Transformed-variable correlation", "Pearson correlation matrix after log(1 + value) transformation."],
    ["09_yearly_growth.png", "Year-over-year growth", "Annual percentage change in global production."],
    ["10_country_comparison.png", "Country production over time", "Historical comparison of the eight largest producers."],
    ["11_random_actual_vs_pred_scatter.png", "Random Forest predictions", "Held-out actual and predicted production values."],
    ["11_xgboost_actual_vs_pred_scatter.png", "XGBoost predictions", "Held-out actual and predicted production values."],
    ["12_random_actual_vs_pred_time.png", "Random Forest forecast examples", "Observed history and one-year-ahead test predictions."],
    ["12_xgboost_actual_vs_pred_time.png", "XGBoost forecast examples", "Observed history and one-year-ahead test predictions."],
    ["13_random_residuals.png", "Random Forest residual diagnostics", "Test residuals versus predictions and residual distribution."],
    ["13_xgboost_residuals.png", "XGBoost residual diagnostics", "Test residuals versus predictions and residual distribution."],
    ["14_feature_importance_selected.png", "Selected-model feature importance", "Relative importance for the selected baseline model."],
    ["15_feature_importance_tuned.png", "Tuned-model feature importance", "Relative importance after hyperparameter tuning."],
  ];
  const gallery = document.getElementById("figure-gallery");
  for (const [filename, title, description] of figures) {
    const figure = document.createElement("figure");
    figure.className = "figure-card card";
    const image = document.createElement("img");
    image.src = `./outputs/figures/${filename}`;
    image.alt = `${title}: ${description}`;
    image.loading = "lazy";
    const caption = document.createElement("figcaption");
    caption.textContent = title;
    const detail = document.createElement("span");
    detail.textContent = description;
    caption.append(detail);
    figure.append(image, caption);
    gallery.append(figure);
  }

  const countrySelect = document.getElementById("prediction-country");
  const cropSelect = document.getElementById("prediction-crop");
  const result = document.getElementById("prediction-result");
  const forecastsByCountry = new Map();
  for (const row of data.forecast) {
    if (!forecastsByCountry.has(row.Country)) forecastsByCountry.set(row.Country, []);
    forecastsByCountry.get(row.Country).push(row);
  }
  const topForecasts = data.forecast
    .slice()
    .sort((a, b) => b.Predicted_Production - a.Predicted_Production)
    .slice(0, 10);
  const forecastCropOrder = [
    "Hazelnuts", "Cashew nuts", "Dates", "Chestnuts", "Walnuts", "Almonds",
    ...Object.keys(cropPalette).filter((crop) =>
      !["Hazelnuts", "Cashew nuts", "Dates", "Chestnuts", "Walnuts", "Almonds"].includes(crop)
    ),
  ];
  renderPlot("global-forecast-chart", forecastCropOrder
    .map((crop) => {
      const rows = topForecasts.filter((row) => row.Dry_Fruit === crop);
      return rows.length ? {
        type: "bar",
        name: crop,
        orientation: "h",
        x: rows.map((row) => row.Predicted_Production),
        y: rows.map((row) => `${row.Country} — ${crop}`),
        marker: { color: forecastPalette[crop] || cropPalette[crop] },
        hovertemplate: "%{y}<br>Predicted production: %{x:,.0f} tonnes<extra></extra>",
      } : null;
    })
    .filter(Boolean), {
    title: "Top 10 country–crop forecasts",
    barmode: "relative",
    xaxis: { title: "Predicted production (tonnes)", rangemode: "tozero" },
    yaxis: { autorange: "reversed" },
    legend: { title: { text: "Crop item" } },
    margin: { l: 190, r: 20, t: 45, b: 65 },
  });
  const countries = [...forecastsByCountry.keys()].sort((a, b) => a.localeCompare(b));
  for (const country of countries) {
    countrySelect.add(new Option(country, country));
  }
  countrySelect.value = countries.includes("India") ? "India" : countries[0];

  function updatePrediction() {
    const rows = forecastsByCountry.get(countrySelect.value) || [];
    const selectedCrop = cropSelect.value;
    const selected = rows.find((row) => row.Dry_Fruit === selectedCrop);
    if (!selected) {
      result.textContent = "No 2025 forecast is available for this country and crop combination.";
      result.classList.add("empty");
      return;
    }
    result.classList.remove("empty");
    result.innerHTML = `<span class="prediction-value">${formatTonnes(selected.Predicted_Production)}</span><span class="prediction-caption">Predicted ${selected.Dry_Fruit} production in ${selected.Country}, ${selected.Year}</span>`;
  }

  function updateCountryForecastChart(rows, country) {
    renderPlot("forecast-country-chart", rows
      .slice()
      .sort((a, b) => a.Dry_Fruit.localeCompare(b.Dry_Fruit))
      .map((row, index) => ({
        type: "bar",
        name: row.Dry_Fruit,
        orientation: "h",
        x: [row.Predicted_Production],
        y: [row.Dry_Fruit],
        marker: { color: forecastPalette[row.Dry_Fruit] || cropPalette[row.Dry_Fruit] || "#636EFA" },
        hovertemplate: "%{y}: %{x:,.0f} tonnes<extra></extra>",
      })), {
      title: `2025 forecast by crop · ${country}`,
      barmode: "group",
      xaxis: { title: "Predicted production (tonnes)", rangemode: "tozero" },
      yaxis: { autorange: "reversed" },
      legend: { title: { text: "Crop item" } },
      margin: { l: 130, r: 24, t: 45, b: 55 },
    });
  }

  function updateCrops() {
    const rows = forecastsByCountry.get(countrySelect.value) || [];
    cropSelect.replaceChildren(...rows
      .slice()
      .sort((a, b) => a.Dry_Fruit.localeCompare(b.Dry_Fruit))
      .map((row) => new Option(row.Dry_Fruit, row.Dry_Fruit)));
    updatePrediction();
    updateCountryForecastChart(rows, countrySelect.value);
  }

  countrySelect.addEventListener("change", updateCrops);
  cropSelect.addEventListener("change", updatePrediction);
  updateCrops();
  status.dataset.ready = "true";
})();
