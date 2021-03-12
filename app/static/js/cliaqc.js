$(document).ready(() => {
  $("#fromDate").val(dayjs().add(-30, "d").format("YYYY-MM-DD"));
  $("#toDate").val(dayjs().format("YYYY-MM-DD"));
});

const updateChart = (chart, data, type) => {
  const fields = [
      { label: "NTC", backgroundColor: "#ff5a5f", borderColor: "#ff5a5f" },
      { label: "PTC", backgroundColor: "#fb8b24", borderColor: "#fb8b24" },
    { label: "NBC_Avg", backgroundColor: "#2862CC", borderColor: "#2862CC" },
    { label: "NTC_Avg", backgroundColor: "#390099", borderColor: "#390099" },
    { label: "PTC_Avg", backgroundColor: "#0466c8", borderColor: "#0466c8" },
    { label: "NBC_CV", backgroundColor: "#45545E", borderColor: "#45545E" },
    { label: "NTC_CV", backgroundColor: "#0091ad", borderColor: "#0091ad" },
    { label: "PTC_CV", backgroundColor: "#2b9348", borderColor: "#2b9348" },
    { label: "Ratio", backgroundColor: "#000", borderColor: "#000" },
  ];
  chart.data.labels = data.map((r) => dayjs(r.created).format("YYYY/MM/DD"));
  chart.data.datasets = fields.map(
    ({ label, backgroundColor, borderColor }) => ({
      label: `${type}-${label}`,
      pointRadius: 4,
      borderWidth: 2,
      pointHoverRadius: 6,
      pointBorderWidth: 1,
      pointBorderColor: "white",
      backgroundColor,
      borderColor,
      fill: false,
      data: data.map((r) => r.result[`${type}_${label}`]), // N7result.map(r=>(r.result[`N7_${label}`])),
    })
  );
  chart.update();
};

document.getElementById("plot").addEventListener("click", (e) => {
  const from = document.getElementById("fromDate").value;
  const to = document.getElementById("toDate").value;
  fetch("http://192.168.1.200:8001/plates/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
    body: JSON.stringify({
      created: {
        $gte: dayjs(from).toISOString(),
        $lte: dayjs(to).toISOString(),
      },
    }),
  })
    .then((res) => {
      return res.json();
    })
    .then((data) => {
      const N7result = data.filter(
        (d) => !d.layout.endsWith("RP4Ctrl") && d.result
      );
      const RP4result = data.filter(
        (d) => d.layout.endsWith("RP4Ctrl") && d.result
      );
      updateChart(N7Chart, N7result, "N7");
      updateChart(RP4Chart, RP4result, "RP4");
      N7datasets = []
      N7result.forEach((r) =>
        N7datasets.push({
          date: dayjs(r.created).format("YYYY/MM/DD"),
          ...r.result,
          N7_Ratio:Number((r.result.N7_PTC_Avg/r.result.N7_NBC_Avg).toFixed(2))
        })
      );
      RP4datasets = []
      RP4result.forEach((r) =>
        RP4datasets.push({
          date: dayjs(r.created).format("YYYY/MM/DD"),
          ...r.result,
          RP4_Ratio:Number((r.result.RP4_PTC_Avg/r.result.RP4_NBC_Avg).toFixed(2))
        })
      );
    })
    .catch((err) => {
      console.log(err);
    });
});

const getCsv = (data) => {
  if (data.length > 0) {
    const header = Object.keys(data[0]);
    const resultArray = [
      header.join(","),
      ...data.map((d) => header.map((h) => d[h]).join(",")),
    ];
    return resultArray.join("\n");
  } else {
    return "";
  }
};

document.getElementById("save").addEventListener("click", (e) => {
  if (N7datasets.length > 0 || RP4datasets.length > 0) {
    const from = document.getElementById("fromDate").value;
    const to = document.getElementById("toDate").value;
    const csv =
      "data:text/csv;charset=utf-8," +
      getCsv(N7datasets) +
      "\n" +
      getCsv(RP4datasets);
    const uri = encodeURI(csv);
    const link = document.createElement("a");
    link.href = uri;
    link.download = `Plates QC ${from} to ${to}.csv`;
    document.body.appendChild(link);
    link.click();
  }
});
