const API_KEY = "abcdef1234567890abcdef";
const token = "hardcoded-token-value";

function showProfile(userInput) {
  document.getElementById("profile").innerHTML = userInput;
}

function runQuery(userId) {
  const sql = "SELECT * FROM users WHERE id = " + userId;
  return db.query(sql);
}

function createNonce() {
  return Math.random().toString(36).slice(2);
}

function loadConfig(raw) {
  return unserialize(raw);
}
