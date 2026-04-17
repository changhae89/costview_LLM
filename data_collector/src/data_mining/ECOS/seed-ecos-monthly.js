/**
 * [SEED SCRIPT] ECOS 월간 과거 데이터 최대치 수집
 * - 시작월: 1960년 1월
 * - 데이터가 없는 초기 구간은 직전 유효값이 없으면 NULL 유지
 */
const axios = require("axios");
const { createClient } = require("@supabase/supabase-js");
const path = require("path");
require("dotenv").config({ path: path.resolve(__dirname, "../../../.env") });

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);
const ECOS_API_KEY = process.env.ECOS_API_KEY;

const START_DATE = "196001";
const END_DATE = (() => {
  const d = new Date();
  const yyyy = d.getFullYear();
  const mm = (d.getMonth() + 1).toString().padStart(2, "0");
  return `${yyyy}${mm}`;
})();

async function fetchEcosMonthlyMaxRange(statCode, itemCode, indicatorName, itemCode2 = null) {
  const itemPath = itemCode2 ? `/${itemCode}/${itemCode2}` : `/${itemCode}`;
  const url = `https://ecos.bok.or.kr/api/StatisticSearch/${ECOS_API_KEY}/json/kr/1/1000/${statCode}/M/${START_DATE}/${END_DATE}${itemPath}`;

  try {
    const response = await axios.get(url);
    if (!response.data?.StatisticSearch?.row) return [];

    return response.data.StatisticSearch.row.map((row) => {
      const yStr = row.TIME.substring(0, 4);
      const mStr = row.TIME.substring(4, 6);
      return {
        reference_date: `${yStr}-${mStr}-01`,
        name: indicatorName,
        value: parseFloat(row.DATA_VALUE),
      };
    });
  } catch (error) {
    console.error(`ECOS seed fetch failed [${indicatorName}]:`, error.message);
    return [];
  }
}

async function seedEcosMonthlyMax() {
  console.log("ECOS 월간 데이터 최대치 수집 시작...");

  const targets = [
    { stat: "401Y015", item: "201121AA", item2: "W", name: "import_price_crude_oil" },
    { stat: "401Y015", item: "201122AA", item2: "W", name: "import_price_natural_gas" },
    { stat: "401Y015", item: "3011AA", item2: "W", name: "import_price_food" },
    { stat: "401Y015", item: "20111AA", item2: "W", name: "import_price_coal" },
    { stat: "404Y014", item: "*AA", name: "ppi_total" },
    { stat: "404Y015", item: "S110AA", name: "ppi_food" },
    { stat: "404Y015", item: "S310AA", name: "ppi_energy" },
  ];

  const dateMap = new Map();
  for (const target of targets) {
    const records = await fetchEcosMonthlyMaxRange(target.stat, target.item, target.name, target.item2);
    records.forEach((rec) => {
      if (!dateMap.has(rec.reference_date)) {
        dateMap.set(rec.reference_date, {
          reference_date: rec.reference_date,
          collected_at: new Date().toISOString(),
        });
      }
      dateMap.get(rec.reference_date)[target.name] = rec.value;
    });
  }

  const columns = targets.map((t) => t.name);
  const sortedDates = [...dateMap.keys()].sort();
  const lastSeen = {};
  columns.forEach((col) => {
    lastSeen[col] = null;
  });

  const finalRows = sortedDates.map((date) => {
    const row = dateMap.get(date);
    columns.forEach((col) => {
      if (row[col] === undefined || row[col] === null || Number.isNaN(row[col])) {
        if (lastSeen[col] !== null) row[col] = lastSeen[col];
      } else {
        lastSeen[col] = row[col];
      }
    });
    return row;
  });

  const { error } = await supabase
    .from("indicator_ecos_monthly_logs")
    .upsert(finalRows, { onConflict: "reference_date" });

  if (error) {
    console.error("ECOS 월간 seed 저장 실패:", error.message);
    return;
  }

  console.log("ECOS 월간 seed 완료");
}

seedEcosMonthlyMax();
