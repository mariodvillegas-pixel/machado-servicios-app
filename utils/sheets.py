import pandas as pd
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import AuthorizedSession
import urllib.parse

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

COLUMNS = [
    "mes", "año", "periodo",
    "energia_kwh", "energia_val",
    "gas_m3", "gas_val",
    "agua_m3", "agua_val", "alc_val",
    "acuerdo_val", "otras_val",
    "pers_p1", "pers_p2", "pers_p3",
    "total_p1", "total_p2", "total_p3",
]

BASE = "https://sheets.googleapis.com/v4/spreadsheets"


class SheetsDB:
    def __init__(self, credentials_dict: dict, sheet_id: str):
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        self._session = AuthorizedSession(creds)
        self._sheet_id = sheet_id
        self._ensure_headers()

    # ── REST helpers ─────────────────────────────────────────────────────────
    def _get(self, range_name: str) -> list:
        enc = urllib.parse.quote(range_name, safe="")
        url = f"{BASE}/{self._sheet_id}/values/{enc}"
        r = self._session.get(url, params={"valueRenderOption": "FORMATTED_VALUE"})
        r.raise_for_status()
        return r.json().get("values", [])

    def _update(self, range_name: str, rows: list):
        enc = urllib.parse.quote(range_name, safe="")
        url = f"{BASE}/{self._sheet_id}/values/{enc}"
        r = self._session.put(
            url,
            json={"range": range_name, "values": rows, "majorDimension": "ROWS"},
            params={"valueInputOption": "USER_ENTERED"},
        )
        r.raise_for_status()

    def _append(self, row: list):
        enc = urllib.parse.quote("A:A", safe="")
        url = f"{BASE}/{self._sheet_id}/values/{enc}:append"
        r = self._session.post(
            url,
            json={"values": [row], "majorDimension": "ROWS"},
            params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
        )
        r.raise_for_status()

    # ── Public API ────────────────────────────────────────────────────────────
    def _ensure_headers(self):
        row1 = self._get("A1:ZZZ1")
        if not row1:
            self._append(COLUMNS)

    def get_all(self) -> pd.DataFrame:
        values = self._get("A:ZZZ")
        if not values or len(values) < 2:
            return pd.DataFrame(columns=COLUMNS)
        headers = values[0]
        rows = values[1:]
        df = pd.DataFrame(rows, columns=headers)
        num_cols = [c for c in COLUMNS if c not in ("mes", "periodo")]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df

    def save_mes(self, data: dict):
        df = self.get_all()
        row = [data.get(col, 0) for col in COLUMNS]

        if not df.empty:
            mask = (df["mes"].astype(str) == str(data.get("mes", ""))) & \
                   (df["año"].astype(str) == str(data.get("año", "")))
            if mask.any():
                idx = int(df[mask].index[0]) + 2  # +1 header, +1 1-based
                self._update(f"A{idx}:ZZZ{idx}", [row])
                return

        self._append(row)

    def get_residentes_ultimo(self) -> tuple:
        df = self.get_all()
        if df.empty:
            return 3, 3, 2
        last = df.iloc[-1]
        return (
            int(last.get("pers_p1", 3)),
            int(last.get("pers_p2", 3)),
            int(last.get("pers_p3", 2)),
        )
