from flask import request, jsonify
from . import slurm_bp
from .job_submitter import submit_slurm_job
from .utils import slurm_sacct, slurm_scancel, slurm_squeue

# =========================
# SUBMIT
# =========================

@slurm_bp.route("/submit", methods=["POST"])
def submit_job():
    data = request.json

    required = ["cmd", "user", "base_name"]
    if any(k not in data for k in required):
        return jsonify({"error": "missing parameters"}), 400

    try:
        job_id = submit_slurm_job(
            cmd=data["cmd"],
            user=data["user"],
            base_name=data["base_name"],
            gpu=data.get("gpu", 1),
            cpus=data.get("cpus", 8),
            mem=data.get("mem", "32G"),
            time=data.get("time", "24:00:00")
        )
        return jsonify({
            "status": "submitted",
            "job_id": job_id
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# STATUS
# =========================

@slurm_bp.route("/status/<job_id>")
def job_status(job_id):
    exit_code, out, err = slurm_sacct(job_id)

    if exit_code != 0:
        return jsonify({"error": err}), 500

    return jsonify({"data": out})


# =========================
# CANCEL
# =========================

@slurm_bp.route("/cancel/<job_id>", methods=["POST"])
def cancel_job(job_id):
    exit_code, out, err = slurm_scancel(job_id)

    if exit_code != 0:
        return jsonify({"error": err}), 500

    return jsonify({"status": "cancelled"})


# =========================
# QUEUE
# =========================

@slurm_bp.route("/queue")
def queue():
    exit_code, out, err = slurm_squeue()

    if exit_code != 0:
        return jsonify({"error": err}), 500

    return jsonify({"data": out})
