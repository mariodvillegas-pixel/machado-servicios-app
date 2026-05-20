import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
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


class SheetsDB:
    def __init__(self, credentials_dict: dict, sheet_id: str):
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        self.ws = client.open_by_key(sheet_id).sheet1
        self._ensure_headers()

    def _ensure_headers(self):
        row1 = self.ws.row_values(1)
        if not row1:
            self.ws.insert_row(COLUMNS, 1)

    def get_all(self) -> pd.DataFrame:
        # Use get_all_values() + manual parsing for broader compatibility
        try:
            values = self.ws.get_all_values()
        except Exception as e:
            # Re-raise with full details so Streamlit shows the real error
            raise RuntimeError(
                f"get_all_values failed [{type(e).__name__}]: {e} | "
                f"ws.title={self.ws.title!r} | ws.id={getattr(self.ws, 'id', '?')!r}"
            ) from e
        if not values or len(values) < 2:
            return pd.DataFrame(columns=COLUMNS)
        headers = values[0]
        rows = values[1:]
        df = pd.DataFrame(rows, columns=headers) if rows else pd.DataFrame(columns=headers)
        # Ensure numeric columns
        num_cols = [c for c in COLUMNS if c not in ("mes", "periodo")]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df

    def save_mes(self, data: dict):
        """Guarda o actualiza el registro del mes."""
        df = self.get_all()
        row = [data.get(col, 0) for col in COLUMNS]

        if not df.empty:
            mask = (df["mes"].astype(str) == str(data.get("mes", ""))) & \
                   (df["año"].astype(str) == str(data.get("año", "")))
            if mask.any():
                idx = int(df[mask].index[0]) + 2  # +1 header, +1 1-based
                self.ws.update(f"A{idx}", [row])
                return

        self.ws.append_row(row)

    def get_residentes_ultimo(self) -> tuple:
        """Retorna residentes del mes más reciente guardado."""
        df = self.get_all()
        if df.empty:
            return 3, 3, 2
        last = df.iloc[-1]
        return (
            int(last.get("pers_p1", 3)),
            int(last.get("pers_p2", 3)),
            int(last.get("pers_p3", 2)),
        )
