function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const { timestamp, question, answer, name, email, organization } = data;

    const spreadsheetId = '1-s0tKT-rLFVfGU24OUaTIalQQDqpZq-oEInksxB4h2Y';
    const sheet = SpreadsheetApp.openById(spreadsheetId).getActiveSheet();

    sheet.appendRow([timestamp, question, answer, name, email, organization]);

    return ContentService
      .createTextOutput(JSON.stringify({ status: 'success' }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: 'error', message: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}