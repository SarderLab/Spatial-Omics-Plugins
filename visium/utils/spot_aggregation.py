from dataclasses import dataclass
from typing import Dict, Tuple, Any, Optional, Union
import pandas as pd
from __future__ import annotations

@dataclass(frozen=True)
class RefMaps:
    main_types: set
    subtype_to_state: Dict[str, Tuple[str, str]]

def _read_celltype_x_spot_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    first_col = df.columns[0]
    if str(first_col).startswith("Unnamed") or first_col in ("", None):
        df = df.rename(columns={first_col: "Main_Type"})

    if df.columns[0] != df.columns[1] and df.columns[0] not in df.columns[1:]:
        df = df.set_index(df.columns[0])

    df = df.apply(pd.to_numeric, errors="coerce").fillna(0.0)    
    df.drop(df.index[-1], inplace=True)
    df.index = df.index.astype(str)
    return df

def build_reference_maps(cell_subtypes_grouped_csv: str) -> RefMaps:
    ref = pd.read_csv(cell_subtypes_grouped_csv).fillna("")

    required = {"Main_Types", "Sub_Types", "Cell_States"}
    missing = required - set(ref.columns)
    if missing:
        raise ValueError(f"Reference CSV missing columns: {sorted(missing)}")

    main_types = set(ref["Main_Types"].astype(str).str.strip())

    subtype_to_state: Dict[str, Tuple[str, str]] = {}
    for _, row in ref.iterrows():
        main = str(row["Main_Types"]).strip()
        subtypes = [s.strip() for s in str(row["Sub_Types"]).split(".") if s.strip()]
        states = [s.strip() for s in str(row["Cell_States"]).split(".") if s.strip()]

        if not subtypes:
            continue
        if len(subtypes) != len(states):
            raise ValueError(
                f"Mismatch in reference for Main_Types='{main}': "
                f"{len(subtypes)} subtypes vs {len(states)} states.\n"
                f"Sub_Types={row['Sub_Types']}\nCell_States={row['Cell_States']}"
            )

        for st, cs in zip(subtypes, states):
            subtype_to_state[st] = (main, cs)

    return RefMaps(main_types=main_types, subtype_to_state=subtype_to_state)

def process_sample_to_spot_json(
    visium_spots,
    predsubclassl1_csv: str,
    predsubclassl2_csv: str,
    cell_subtypes_grouped_csv: str,
) -> Dict[str, Dict[str, Any]]:
    maps = build_reference_maps(cell_subtypes_grouped_csv)

    l1 = _read_celltype_x_spot_csv(predsubclassl1_csv)
    l2 = _read_celltype_x_spot_csv(predsubclassl2_csv)

    spots = [str(spot['properties']['barcode']) for spot in visium_spots['features']]
    common_spots = [c for c in spots if c in set(l1.columns) and c in set(l2.columns)]
    assert set(spots) == set(common_spots), ValueError("We have some spots missing")

    out: Dict[str, Dict[str, Any]] = {}
    for spot, spot_id in zip(visium_spots['features'], spots):
        # --- Main_Cell_Types (from L1) ---
        main_cell_types: Dict[str, float] = {}
        for cell_type, frac in l1[spot_id].items():
            ct = str(cell_type).strip()
            if ct in maps.main_types:
                f = float(frac)
                if f != 0.0:
                    main_cell_types[ct] = f

        # --- Cell_States (from L2) ---
        cell_states: Dict[str, Dict[str, float]] = {}
        for subtype, frac in l2[spot_id].items():
            st = str(subtype).strip()
            if st not in maps.subtype_to_state:
                continue
            main, state = maps.subtype_to_state[st]
            f = float(frac)
            if f == 0.0:
                continue

            cell_states.setdefault(main, {})
            cell_states[main][state] = cell_states[main].get(state, 0.0) + f

        spot['properties'] = spot['properties'] |  {
            "Main_Cell_Types": main_cell_types,
            "Cell_States": cell_states,
        }

    return visium_spots