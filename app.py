from __future__ import annotations

import os
import tempfile
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from flask import Flask, flash, redirect, render_template, request, send_file, url_for


@dataclass
class UploadRecord:
    path: str
    headers: List[str]


@dataclass
class ResultRecord:
    path: str
    summary: Dict[str, Any]
    logs: List[Dict[str, str]]


app = Flask(__name__)
app.secret_key = "network-tools-secret"

UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "network_tools")
os.makedirs(UPLOAD_DIR, exist_ok=True)

uploads: Dict[str, UploadRecord] = {}
results: Dict[str, ResultRecord] = {}


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.post("/upload")
def upload_excel() -> str:
    file = request.files.get("excel_file")
    if not file or not file.filename:
        flash("请先选择 Excel 文件。", "error")
        return redirect(url_for("index"))

    token = uuid.uuid4().hex
    filename = f"upload_{token}.xlsx"
    path = os.path.join(UPLOAD_DIR, filename)
    file.save(path)

    df = pd.read_excel(path)
    headers = [str(col) for col in df.columns]
    uploads[token] = UploadRecord(path=path, headers=headers)

    return render_template("configure.html", token=token, headers=headers)


@app.post("/process")
def process_excel() -> str:
    token = request.form.get("token", "")
    record = uploads.get(token)
    if not record:
        flash("上传记录已失效，请重新上传 Excel。", "error")
        return redirect(url_for("index"))

    mode = request.form.get("mode", "geocode")
    provider = request.form.get("provider", "mapbox")
    provider_key = request.form.get("provider_api_key", "").strip()
    reverse_column_mode = request.form.get("reverse_column_mode", "separate")
    reverse_delimiter_mode = request.form.get("reverse_delimiter_mode", "auto")
    reverse_delimiter = request.form.get("reverse_delimiter", ",")

    custom_app_id = request.form.get("custom_app_id", "").strip()
    custom_credential = request.form.get("custom_credential", "").strip()
    custom_token_url = request.form.get("custom_token_url", "").strip()
    custom_geocode_url = request.form.get("custom_geocode_url", "").strip()

    df = pd.read_excel(record.path)
    logs: List[Dict[str, str]] = []

    if provider == "custom" and mode != "geocode":
        flash("自定义接口仅支持地址编码。", "error")
        return redirect(url_for("index"))

    if provider != "custom" and not provider_key:
        flash("请填写 API Key。", "error")
        return redirect(url_for("index"))

    if mode == "geocode":
        address_column = request.form.get("address_column", "")
        if not address_column:
            flash("请选择地址列名。", "error")
            return redirect(url_for("index"))
        df["纬度"] = ""
        df["经度"] = ""
        for idx, address in df[address_column].items():
            result = geocode_address(
                str(address),
                provider,
                provider_key,
                custom_app_id,
                custom_credential,
                custom_token_url,
                custom_geocode_url,
            )
            if result.success:
                df.at[idx, "纬度"] = result.lat
                df.at[idx, "经度"] = result.lng
            else:
                logs.append(result.log_entry)
    elif mode == "reverse":
        df["解析地址"] = ""
        df["一级行政区"] = ""
        df["二级行政区"] = ""
        df["三级行政区"] = ""
        if reverse_column_mode == "single":
            reverse_column = request.form.get("reverse_column", "")
            if not reverse_column:
                flash("请选择经纬度列名。", "error")
                return redirect(url_for("index"))
            for idx, raw in df[reverse_column].items():
                lat, lng = parse_lat_lng(str(raw), reverse_delimiter_mode, reverse_delimiter)
                result = reverse_geocode(lat, lng, provider, provider_key)
                if result.success:
                    df.at[idx, "解析地址"] = result.address
                    df.at[idx, "一级行政区"] = result.admin1
                    df.at[idx, "二级行政区"] = result.admin2
                    df.at[idx, "三级行政区"] = result.admin3
                else:
                    logs.append(result.log_entry)
        else:
            lat_column = request.form.get("lat_column", "")
            lng_column = request.form.get("lng_column", "")
            if not lat_column or not lng_column:
                flash("请选择经度与纬度列名。", "error")
                return redirect(url_for("index"))
            for idx, row in df.iterrows():
                lat = row.get(lat_column)
                lng = row.get(lng_column)
                result = reverse_geocode(lat, lng, provider, provider_key)
                if result.success:
                    df.at[idx, "解析地址"] = result.address
                    df.at[idx, "一级行政区"] = result.admin1
                    df.at[idx, "二级行政区"] = result.admin2
                    df.at[idx, "三级行政区"] = result.admin3
                else:
                    logs.append(result.log_entry)
    else:
        start_column = request.form.get("start_column", "")
        end_column = request.form.get("end_column", "")
        if not start_column or not end_column:
            flash("请选择起点与终点列名。", "error")
            return redirect(url_for("index"))
        df["导航距离(km)"] = ""
        df["导航时间(min)"] = ""
        for idx, row in df.iterrows():
            origin = str(row.get(start_column, ""))
            destination = str(row.get(end_column, ""))
            origin_geo = geocode_address(origin, provider, provider_key, "", "", "", "")
            destination_geo = geocode_address(destination, provider, provider_key, "", "", "", "")
            if not origin_geo.success or not destination_geo.success:
                logs.append(
                    {
                        "address": f"{origin} -> {destination}",
                        "type": "geocode_error",
                        "request": "geocode",
                        "response": "无法解析起终点坐标",
                    }
                )
                continue
            route = fetch_route(
                origin_geo.lat,
                origin_geo.lng,
                destination_geo.lat,
                destination_geo.lng,
                provider,
                provider_key,
            )
            if route.success:
                df.at[idx, "导航距离(km)"] = route.distance_km
                df.at[idx, "导航时间(min)"] = route.duration_min
            else:
                logs.append(route.log_entry)

    result_token = uuid.uuid4().hex
    result_path = os.path.join(UPLOAD_DIR, f"result_{result_token}.xlsx")
    df.to_excel(result_path, index=False)
    summary = {
        "mode": mode,
        "provider": provider,
        "row_count": len(df.index),
        "error_count": len(logs),
    }
    results[result_token] = ResultRecord(path=result_path, summary=summary, logs=logs)

    return render_template(
        "result.html",
        token=result_token,
        summary=summary,
        logs=logs,
    )


@app.get("/download/<token>")
def download_result(token: str):
    record = results.get(token)
    if not record:
        flash("结果已过期，请重新处理。", "error")
        return redirect(url_for("index"))
    return send_file(record.path, as_attachment=True)


@dataclass
class GeocodeResult:
    success: bool
    lat: Optional[float] = None
    lng: Optional[float] = None
    log_entry: Optional[Dict[str, str]] = None


@dataclass
class ReverseResult:
    success: bool
    address: str = ""
    admin1: str = ""
    admin2: str = ""
    admin3: str = ""
    log_entry: Optional[Dict[str, str]] = None


@dataclass
class RouteResult:
    success: bool
    distance_km: str = ""
    duration_min: str = ""
    log_entry: Optional[Dict[str, str]] = None


def geocode_address(
    address: str,
    provider: str,
    provider_key: str,
    custom_app_id: str,
    custom_credential: str,
    custom_token_url: str,
    custom_geocode_url: str,
) -> GeocodeResult:
    if not address:
        return GeocodeResult(
            success=False,
            log_entry={
                "address": address,
                "type": "empty",
                "request": "geocode",
                "response": "地址为空",
            },
        )

    encoded = requests.utils.quote(address)
    if provider == "custom":
        token = fetch_custom_token(custom_app_id, custom_credential, custom_token_url)
        if not token:
            return GeocodeResult(
                success=False,
                log_entry={
                    "address": address,
                    "type": "auth_error",
                    "request": custom_token_url or "getResAppDynamicToken",
                    "response": "无法获取自定义接口 Token",
                },
            )
        url = custom_geocode_url or "geographicSearch"
        try:
            response = requests.post(
                url,
                json={"address": address, "language": "en", "coordType": "wgs84"},
                headers={"Authorization": token},
                timeout=10,
            )
            body = response.json()
        except requests.RequestException as exc:
            return GeocodeResult(
                success=False,
                log_entry={
                    "address": address,
                    "type": "network_error",
                    "request": url,
                    "response": str(exc),
                },
            )
        if not response.ok or body.get("result", {}).get("status") != "OK":
            return GeocodeResult(
                success=False,
                log_entry={
                    "address": address,
                    "type": "network_error",
                    "request": url,
                    "response": str(body),
                },
            )
        location = body.get("result", {}).get("geometry", {}).get("location")
        if not location:
            return GeocodeResult(
                success=False,
                log_entry={
                    "address": address,
                    "type": "no_result",
                    "request": url,
                    "response": str(body),
                },
            )
        return GeocodeResult(success=True, lat=location.get("lat"), lng=location.get("lng"))

    if provider == "mapbox":
        url = (
            "https://api.mapbox.com/geocoding/v5/mapbox.places/"
            f"{encoded}.json?access_token={provider_key}"
        )
        try:
            response = requests.get(url, timeout=10)
            body = response.json()
        except requests.RequestException as exc:
            return GeocodeResult(
                success=False,
                log_entry={
                    "address": address,
                    "type": "network_error",
                    "request": url,
                    "response": str(exc),
                },
            )
        if not response.ok or not body.get("features"):
            return GeocodeResult(
                success=False,
                log_entry={
                    "address": address,
                    "type": "no_result",
                    "request": url,
                    "response": str(body),
                },
            )
        lng, lat = body["features"][0]["center"]
        return GeocodeResult(success=True, lat=lat, lng=lng)

    url = f"https://geocode.search.hereapi.com/v1/geocode?q={encoded}&apiKey={provider_key}"
    try:
        response = requests.get(url, timeout=10)
        body = response.json()
    except requests.RequestException as exc:
        return GeocodeResult(
            success=False,
            log_entry={
                "address": address,
                "type": "network_error",
                "request": url,
                "response": str(exc),
            },
        )
    if not response.ok or not body.get("items"):
        return GeocodeResult(
            success=False,
            log_entry={
                "address": address,
                "type": "no_result",
                "request": url,
                "response": str(body),
            },
        )
    position = body["items"][0]["position"]
    return GeocodeResult(success=True, lat=position.get("lat"), lng=position.get("lng"))


def fetch_custom_token(app_id: str, credential: str, token_url: str) -> str:
    url = token_url or "getResAppDynamicToken"
    try:
        response = requests.post(
            url,
            json={"appId": app_id, "credential": credential},
            timeout=10,
        )
        body = response.json()
    except requests.RequestException:
        return ""
    if not response.ok or body.get("status", {}).get("statusCode") != "SUCESS":
        return ""
    return str(body.get("result", ""))


def reverse_geocode(lat: Any, lng: Any, provider: str, provider_key: str) -> ReverseResult:
    try:
        lat_value = float(lat)
        lng_value = float(lng)
    except (TypeError, ValueError):
        return ReverseResult(
            success=False,
            log_entry={
                "address": f"{lat},{lng}",
                "type": "invalid_coord",
                "request": "reverse",
                "response": "经纬度格式无效",
            },
        )

    if provider == "mapbox":
        url = (
            "https://api.mapbox.com/geocoding/v5/mapbox.places/"
            f"{lng_value},{lat_value}.json?access_token={provider_key}"
        )
        try:
            response = requests.get(url, timeout=10)
            body = response.json()
        except requests.RequestException as exc:
            return ReverseResult(
                success=False,
                log_entry={
                    "address": f"{lat},{lng}",
                    "type": "network_error",
                    "request": url,
                    "response": str(exc),
                },
            )
        if not response.ok or not body.get("features"):
            return ReverseResult(
                success=False,
                log_entry={
                    "address": f"{lat},{lng}",
                    "type": "no_result",
                    "request": url,
                    "response": str(body),
                },
            )
        feature = body["features"][0]
        admin1, admin2, admin3 = extract_mapbox_admin(feature.get("context", []))
        return ReverseResult(
            success=True,
            address=feature.get("place_name", ""),
            admin1=admin1,
            admin2=admin2,
            admin3=admin3,
        )

    url = (
        "https://revgeocode.search.hereapi.com/v1/revgeocode"
        f"?at={lat_value},{lng_value}&lang=zh-CN&apiKey={provider_key}"
    )
    try:
        response = requests.get(url, timeout=10)
        body = response.json()
    except requests.RequestException as exc:
        return ReverseResult(
            success=False,
            log_entry={
                "address": f"{lat},{lng}",
                "type": "network_error",
                "request": url,
                "response": str(exc),
            },
        )
    if not response.ok or not body.get("items"):
        return ReverseResult(
            success=False,
            log_entry={
                "address": f"{lat},{lng}",
                "type": "no_result",
                "request": url,
                "response": str(body),
            },
        )
    item = body["items"][0]
    address = item.get("address", {})
    return ReverseResult(
        success=True,
        address=item.get("title", ""),
        admin1=address.get("state") or address.get("province", ""),
        admin2=address.get("city") or address.get("county", ""),
        admin3=address.get("district") or address.get("subdistrict", ""),
    )


def fetch_route(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    provider: str,
    provider_key: str,
) -> RouteResult:
    if provider == "mapbox":
        url = (
            "https://api.mapbox.com/directions/v5/mapbox/driving/"
            f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
            f"?geometries=geojson&overview=full&access_token={provider_key}"
        )
        try:
            response = requests.get(url, timeout=10)
            body = response.json()
        except requests.RequestException as exc:
            return RouteResult(
                success=False,
                log_entry={
                    "address": f"{origin_lat},{origin_lng} -> {dest_lat},{dest_lng}",
                    "type": "network_error",
                    "request": url,
                    "response": str(exc),
                },
            )
        if not response.ok or not body.get("routes"):
            return RouteResult(
                success=False,
                log_entry={
                    "address": f"{origin_lat},{origin_lng} -> {dest_lat},{dest_lng}",
                    "type": "no_result",
                    "request": url,
                    "response": str(body),
                },
            )
        route = body["routes"][0]
        return RouteResult(
            success=True,
            distance_km=f"{route.get('distance', 0) / 1000:.2f}",
            duration_min=str(round(route.get("duration", 0) / 60)),
        )

    url = (
        "https://router.hereapi.com/v8/routes"
        f"?transportMode=car&origin={origin_lat},{origin_lng}"
        f"&destination={dest_lat},{dest_lng}&return=summary&apiKey={provider_key}"
    )
    try:
        response = requests.get(url, timeout=10)
        body = response.json()
    except requests.RequestException as exc:
        return RouteResult(
            success=False,
            log_entry={
                "address": f"{origin_lat},{origin_lng} -> {dest_lat},{dest_lng}",
                "type": "network_error",
                "request": url,
                "response": str(exc),
            },
        )
    routes = body.get("routes") if response.ok else None
    if not response.ok or not routes:
        return RouteResult(
            success=False,
            log_entry={
                "address": f"{origin_lat},{origin_lng} -> {dest_lat},{dest_lng}",
                "type": "no_result",
                "request": url,
                "response": str(body),
            },
        )
    summary = routes[0]["sections"][0]["summary"]
    return RouteResult(
        success=True,
        distance_km=f"{summary.get('length', 0) / 1000:.2f}",
        duration_min=str(round(summary.get("duration", 0) / 60)),
    )


def extract_mapbox_admin(context: List[Dict[str, Any]]) -> Tuple[str, str, str]:
    place = next((item.get("text", "") for item in context if item.get("id", "").startswith("place")), "")
    district = next((item.get("text", "") for item in context if item.get("id", "").startswith("district")), "")
    region = next((item.get("text", "") for item in context if item.get("id", "").startswith("region")), "")
    locality = next((item.get("text", "") for item in context if item.get("id", "").startswith("locality")), "")
    admin1 = region or place
    admin2 = place or locality
    admin3 = district or locality
    return admin1, admin2, admin3


def parse_lat_lng(raw: str, mode: str, delimiter: str) -> Tuple[Optional[float], Optional[float]]:
    if not raw:
        return None, None
    if mode == "auto":
        for sep in [",", "，", " ", "|", ";"]:
            if sep in raw:
                parts = [part for part in raw.split(sep) if part]
                if len(parts) >= 2:
                    return parse_lat_lng_values(parts[0], parts[1])
        return None, None
    parts = [part for part in raw.split(delimiter) if part]
    if len(parts) < 2:
        return None, None
    return parse_lat_lng_values(parts[0], parts[1])


def parse_lat_lng_values(lat: str, lng: str) -> Tuple[Optional[float], Optional[float]]:
    try:
        return float(lat), float(lng)
    except ValueError:
        return None, None


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
