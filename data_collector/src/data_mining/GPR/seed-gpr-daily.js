const axios = require("axios");
const csv = require("csv-parser");
const { Readable } = require("stream");
const { createClient } = require("@supabase/supabase-js");
const path = require("path");
require("dotenv").config({ path: path.resolve(__dirname, "../../../.env") }); // 경로 주의!

const supabase = createClient(process.env.SUPABASE_URL, process.env.SUPABASE_KEY);

async function seedDailyGPR() {
    const url = "https://www.matteoiacoviello.com/ai_gpr_files/ai_gpr_data_daily.csv";

    try {
        console.log("⏳ 일일 데이터(2023~현재) 수집 중...");
        const response = await axios.get(url, { responseType: "arraybuffer" });
        const rows = [];

        await new Promise((resolve, reject) => {
            Readable.from(response.data.toString())
                .pipe(csv())
                .on("data", (row) => rows.push(row))
                .on("end", resolve)
                .on("error", reject);
        });

        // ✅ 2023년 1월 1일 이후 데이터만 필터링
        const filteredRows = rows.filter(row => row.Date >= '2023-01-01');
        console.log(`🔍 필터링된 데이터 개수: ${filteredRows.length}개`);

        const records = filteredRows.map(row => ({
            ai_gpr_index: parseFloat(row["GPR_AI"]),
            oil_disruptions: parseFloat(row["GPR_OIL"] || 0),
            gpr_original: parseFloat(row["GPR_AER"] || 0),
            non_oil_gpr: parseFloat(row["GPR_NONOIL"] || 0),
            reference_date: row["Date"],
        }));

        // 대시보드·API와 동일 테이블 (fetch-gpr-daily.js 와 맞춤)
        const { error } = await supabase
            .from("indicator_gpr_daily_logs")
            .upsert(records, { onConflict: "reference_date" });

        if (error) throw error;
        console.log(`✅ 2023년~현재까지의 일일 데이터 ${records.length}개 삽입 완료!`);

    } catch (error) {
        console.error("❌ Seed 작업 실패:", error.message);
    }
}

seedDailyGPR();