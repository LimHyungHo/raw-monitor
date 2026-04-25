from flask import Blueprint, flash, redirect, render_template, request, url_for
from urllib.parse import urlencode

from app.services.change_history_service import ChangeHistoryService
from app.services.gpt_compare_service import GPTCompareService
from app.services.latest_pdf_service import LatestPdfService
from app.services.monitoring_service import MonitoringService
from app.services.monitoring_target_service import MonitoringTargetService

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def home():
    return redirect(url_for("web.monitoring_list"))


@web_bp.get("/monitoring")
def monitoring_list():
    email = (request.args.get("email") or "").strip()
    name = (request.args.get("name") or "").strip()
    service = MonitoringTargetService()
    targets = service.list_monitoring_targets(
        email=email or None,
        name=name or None,
        active_only=False,
    ) if (email or name) else []

    return render_template(
        "monitoring/list.html",
        email=email,
        name=name,
        targets=targets,
        form_data={
            "email": email,
            "name": name,
            "user_name": "",
            "document_name": "",
            "target_type": "law",
            "keywords": "",
            "document_id": "",
            "notify_email": email,
        },
    )


@web_bp.post("/monitoring/run")
def monitoring_run():
    email = (request.form.get("email") or "").strip()
    name = (request.form.get("name") or "").strip()
    require_selection = (request.form.get("require_selection") or "").strip() == "1"
    target_ids = [value.strip() for value in request.form.getlist("target_ids") if value.strip()]

    if require_selection and not target_ids:
        flash("모니터링 실행할 대상을 선택해 주세요.", "error popup")
        return redirect(url_for("web.monitoring_list", email=email, name=name))

    try:
        service = MonitoringService()
        results = service.run(target_ids=target_ids or None)
        changed_count = sum(
            1
            for result in results
            if result.get("status") in {"changed", "backfilled_changed"}
        )
        initialized_count = sum(1 for result in results if result.get("status") == "initialized")
        unchanged_count = sum(1 for result in results if result.get("status") == "unchanged")
        error_count = sum(1 for result in results if result.get("status") == "error")
        flash(
            "모니터링 실행 완료: "
            f"변경 {changed_count}건, 최초저장 {initialized_count}건, "
            f"무변경 {unchanged_count}건, 오류 {error_count}건",
            "success",
        )
        if error_count:
            failed_messages = []
            for result in results:
                if result.get("status") != "error":
                    continue
                document_name = result.get("document_name", "알 수 없는 대상")
                error_message = result.get("error", "오류 원인 미상")
                failed_messages.append(f"{document_name}: {error_message}")
            flash("실패 대상: " + " | ".join(failed_messages), "error")
    except Exception as exc:
        flash(f"모니터링 실행 중 오류가 발생했습니다: {exc}", "error")

    if email or name:
        return redirect(_build_change_list_url(email=email, name=name, target_ids=target_ids))
    return redirect(url_for("web.monitoring_list"))


@web_bp.post("/monitoring")
def monitoring_create():
    form = request.form
    email = (form.get("email") or "").strip()
    user_name = (form.get("user_name") or "").strip() or None
    document_name = (form.get("document_name") or "").strip()
    target_type = (form.get("target_type") or "").strip()
    document_id = (form.get("document_id") or "").strip() or None
    notify_email = (form.get("notify_email") or "").strip() or None
    keywords_raw = form.get("keywords") or ""

    form_data = {
        "email": email,
        "name": "",
        "user_name": user_name or "",
        "document_name": document_name,
        "target_type": target_type,
        "keywords": keywords_raw,
        "document_id": document_id or "",
        "notify_email": notify_email or "",
    }

    try:
        service = MonitoringTargetService()
        result = service.register_monitoring(
            email=email,
            user_name=user_name,
            document_name=document_name,
            target_type=target_type,
            document_id=document_id,
            notify_email=notify_email,
            keywords=_split_keywords(keywords_raw),
        )
        flash(
            f"{result['target']['document_name']} 모니터링이 등록되었습니다.",
            "success",
        )
        return redirect(url_for("web.monitoring_list", email=result["user"]["email"]))
    except ValueError as exc:
        flash(str(exc), "error")
    except Exception as exc:
        flash(f"등록 중 오류가 발생했습니다: {exc}", "error")

    service = MonitoringTargetService()
    targets = service.list_monitoring_targets(email=email, active_only=False) if email else []
    return render_template(
        "monitoring/list.html",
        email=email,
        name="",
        targets=targets,
        form_data=form_data,
    ), 400


@web_bp.post("/monitoring/<int:target_id>/deactivate")
def monitoring_deactivate(target_id):
    email = (request.form.get("email") or "").strip()
    name = (request.form.get("name") or "").strip()
    try:
        service = MonitoringTargetService()
        target = service.deactivate_target(target_id)
        if target:
            flash(f"{target['document_name']} 모니터링을 비활성화했습니다.", "success")
        else:
            flash("대상을 찾지 못했습니다.", "error")
    except Exception as exc:
        flash(f"비활성화 중 오류가 발생했습니다: {exc}", "error")

    return redirect(url_for("web.monitoring_list", email=email, name=name))


@web_bp.post("/monitoring/<int:target_id>/send-latest-pdf")
def monitoring_send_latest_pdf(target_id):
    email = (request.form.get("email") or "").strip()
    name = (request.form.get("name") or "").strip()

    try:
        service = LatestPdfService()
        result = service.send_latest_pdf(target_id)
        flash(
            f"{result['target']['document_name']} 최신 PDF를 {result['recipient_email']}로 발송했습니다.",
            "success popup",
        )
    except Exception as exc:
        flash(f"최신 PDF 발송 중 오류가 발생했습니다: {exc}", "error popup")

    return redirect(url_for("web.monitoring_list", email=email, name=name))


@web_bp.get("/changes")
def change_list():
    email = (request.args.get("email") or "").strip()
    name = (request.args.get("name") or "").strip()
    require_selection = (request.args.get("require_selection") or "").strip() == "1"
    target_ids = [value.strip() for value in request.args.getlist("target_ids") if value.strip()]
    normalized_target_ids = [target_id for target_id in target_ids if target_id.isdigit()]

    if require_selection and not normalized_target_ids:
        flash("변경 이력을 볼 대상을 선택해 주세요.", "error popup")
        return redirect(url_for("web.monitoring_list", email=email, name=name))

    service = ChangeHistoryService()
    changes = service.list_changes(
        email=email or None,
        name=name or None,
        target_ids=normalized_target_ids or None,
    ) if (email or name) else []

    selected_targets = []
    if normalized_target_ids and (email or name):
        target_service = MonitoringTargetService()
        selected_targets = [
            target
            for target in target_service.list_monitoring_targets(
                email=email or None,
                name=name or None,
                active_only=False,
            )
            if str(target["id"]) in normalized_target_ids
        ]

    return render_template(
        "changes/list.html",
        email=email,
        name=name,
        changes=changes,
        selected_target_ids=normalized_target_ids,
        selected_targets=selected_targets,
    )


@web_bp.get("/changes/<int:change_set_id>")
def change_detail(change_set_id):
    service = ChangeHistoryService()
    detail = service.get_change_detail(change_set_id)
    if not detail:
        flash("변경 이력을 찾지 못했습니다.", "error")
        return redirect(url_for("web.change_list"))

    back_context = _get_change_back_context_from_request(request.args)

    return render_template(
        "changes/detail.html",
        detail=detail,
        gpt_analysis=None,
        back_context=back_context,
    )


@web_bp.post("/changes/<int:change_set_id>/analyze-gpt")
def change_detail_analyze_gpt(change_set_id):
    history_service = ChangeHistoryService()
    detail = history_service.get_change_detail(change_set_id)
    if not detail:
        flash("변경 이력을 찾지 못했습니다.", "error")
        return redirect(url_for("web.change_list"))

    back_context = _get_change_back_context_from_request(request.form)
    gpt_analysis = None
    try:
        gpt_analysis = GPTCompareService().analyze_change_detail(detail)
        flash("GPT 비교 분석을 완료했습니다.", "success popup")
    except Exception as exc:
        flash(f"GPT 비교 분석 중 오류가 발생했습니다: {exc}", "error popup")

    return render_template(
        "changes/detail.html",
        detail=detail,
        gpt_analysis=gpt_analysis,
        back_context=back_context,
    )


def _split_keywords(value):
    raw_parts = []
    for line in str(value).replace(",", "\n").splitlines():
        raw_parts.append(line.strip())
    return [part for part in raw_parts if part]


def _build_change_list_url(*, email="", name="", target_ids=None):
    query = {}
    if email:
        query["email"] = email
    if name:
        query["name"] = name
    if target_ids:
        normalized_target_ids = [str(target_id).strip() for target_id in target_ids if str(target_id).strip()]
        if normalized_target_ids:
            query["target_ids"] = normalized_target_ids

    base_url = url_for("web.change_list")
    if not query:
        return base_url
    return f"{base_url}?{urlencode(query, doseq=True)}"


def _get_change_back_context_from_request(source):
    email = (source.get("email") or "").strip()
    name = (source.get("name") or "").strip()
    target_ids = [value.strip() for value in source.getlist("target_ids") if value.strip()]
    return {
        "email": email,
        "name": name,
        "target_ids": target_ids,
        "list_url": _build_change_list_url(email=email, name=name, target_ids=target_ids),
    }
