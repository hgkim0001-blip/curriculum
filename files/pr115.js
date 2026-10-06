/**
 * 기상청 API 허브 중기예보 자동 수집 스크립트 (Google Apps Script)
 * ------------------------------------------------------------
 * 이 스크립트가 하는 일:
 *   1) 기상청 API 허브에서 전국 10개 권역의 중기예보(기온·강수확률)를 가져온다.
 *   2) 결과를 이 스프레드시트의 "수집로그" 시트에 한 줄씩 追加(append)한다.
 *   3) 시간 기반 트리거를 걸어두면, 사람이 아무것도 안 해도 매일 자동으로 실행된다.
 *
 * 사용 전 꼭 할 일:
 *   - AUTH_KEY에 발급받은 인증키를 넣는다.
 *   - 스프레드시트에 "수집로그"라는 이름의 시트를 만들어둔다(없으면 스크립트가 자동 생성).
 *   - Apps Script 편집기에서 setupTrigger()를 한 번 실행해 자동 실행을 등록한다.
 */

const AUTH_KEY = "여기에_발급받은_인증키_입력";
const SHEET_NAME = "수집로그";

const REGIONS = {
  "서울·인천·경기": { land: "11B00000", temp: "11B10101" },
  "강원영서":       { land: "11D10000", temp: "11D10301" },
  "강원영동":       { land: "11D20000", temp: "11D20501" },
  "충청북도":       { land: "11C10000", temp: "11C10301" },
  "대전·세종·충남": { land: "11C20000", temp: "11C20401" },
  "전북":          { land: "11F10000", temp: "11F10201" },
  "광주·전남":      { land: "11F20000", temp: "11F20501" },
  "대구·경북":      { land: "11H10000", temp: "11H10701" },
  "부산·울산·경남": { land: "11H20000", temp: "11H20201" },
  "제주도":         { land: "11G00000", temp: "11G00201" },
};

// ------------------------------------------------------------------
// 매일 자동으로 실행될 메인 함수
// ------------------------------------------------------------------
function collectWeatherForecast() {
  const sheet = getOrCreateSheet_();
  const now = new Date();
  const tmFcInfo = computeTmFc_(now);

  const rows = [];
  for (const regionName in REGIONS) {
    const codes = REGIONS[regionName];
    const landItem = callApi_("getMidLandFcst", codes.land, tmFcInfo.tmFc);
    const tempItem = callApi_("getMidTa", codes.temp, tmFcInfo.tmFc);

    // 4일 후 ~ 10일 후까지, 실제 달력 날짜로 환산해서 기록
    for (let offset = 4; offset <= 10; offset++) {
      const targetDate = new Date(tmFcInfo.baseDate);
      targetDate.setDate(targetDate.getDate() + offset);

      const taMin = tempItem ? tempItem["taMin" + offset] : null;
      const taMax = tempItem ? tempItem["taMax" + offset] : null;
      let weather = null, rain = null;
      if (landItem) {
        if (offset <= 7) {
          const wfAm = landItem["wf" + offset + "Am"];
          const wfPm = landItem["wf" + offset + "Pm"];
          weather = (wfAm === wfPm) ? wfAm : (wfAm + "/" + wfPm);
          rain = landItem["rnSt" + offset + "Am"] + "~" + landItem["rnSt" + offset + "Pm"] + "%";
        } else {
          weather = landItem["wf" + offset];
          rain = landItem["rnSt" + offset] + "%";
        }
      }

      rows.push([
        Utilities.formatDate(now, "Asia/Seoul", "yyyy-MM-dd HH:mm"),  // 수집일시
        tmFcInfo.tmFc,                                                 // 발표시각(기준)
        regionName,
        Utilities.formatDate(targetDate, "Asia/Seoul", "yyyy-MM-dd"),  // 대상 날짜
        taMin, taMax, weather, rain,
      ]);
    }
  }

  if (rows.length > 0) {
    sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, rows[0].length).setValues(rows);
  }
  Logger.log(rows.length + "행 기록 완료");
}

// ------------------------------------------------------------------
// 헬퍼 함수들
// ------------------------------------------------------------------
function getOrCreateSheet_() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow(["수집일시", "발표시각(기준)", "지역", "대상날짜", "최저기온", "최고기온", "날씨", "강수확률"]);
  }
  return sheet;
}

function computeTmFc_(now) {
  const seoulNow = new Date(Utilities.formatDate(now, "Asia/Seoul", "yyyy-MM-dd'T'HH:mm:ss"));
  const hour = seoulNow.getHours();
  const base = new Date(seoulNow);
  let fcHour;
  if (hour >= 18) { fcHour = 18; }
  else if (hour >= 6) { fcHour = 6; }
  else { base.setDate(base.getDate() - 1); fcHour = 18; }
  base.setHours(fcHour, 0, 0, 0);

  const tmFc = Utilities.formatDate(base, "Asia/Seoul", "yyyyMMdd") + (fcHour === 6 ? "0600" : "1800");
  return { tmFc: tmFc, baseDate: base };
}

function callApi_(operation, regId, tmFc) {
  const url = "https://apihub.kma.go.kr/api/typ02/openApi/MidFcstInfoService/" + operation
    + "?pageNo=1&numOfRows=10&dataType=JSON&regId=" + regId + "&tmFc=" + tmFc + "&authKey=" + AUTH_KEY;
  try {
    const res = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
    const data = JSON.parse(res.getContentText());
    const header = data.response && data.response.header;
    if (!header || header.resultCode !== "00") {
      Logger.log(operation + "(" + regId + ") 오류: " + JSON.stringify(data).substring(0, 300));
      return null;
    }
    const items = data.response.body.items.item;
    return items && items.length > 0 ? items[0] : null;
  } catch (e) {
    Logger.log(operation + "(" + regId + ") 예외: " + e);
    return null;
  }
}

// ------------------------------------------------------------------
// 자동 실행(트리거) 등록 — 이 함수는 딱 한 번만 실행하면 됨
// ------------------------------------------------------------------
function setupTrigger() {
  // 기존에 같은 이름으로 등록된 트리거가 있으면 중복 등록 방지를 위해 먼저 지운다
  const triggers = ScriptApp.getProjectTriggers();
  for (const t of triggers) {
    if (t.getHandlerFunction() === "collectWeatherForecast") {
      ScriptApp.deleteTrigger(t);
    }
  }
  // 매일 오전 7시(기상청 06시 발표 이후) 자동 실행되도록 등록
  ScriptApp.newTrigger("collectWeatherForecast")
    .timeBased()
    .everyDays(1)
    .atHour(7)
    .inTimezone("Asia/Seoul")
    .create();
  Logger.log("트리거 등록 완료: 매일 오전 7시 자동 실행");
}
