def run_learning_loop() -> Dict[str, Any]:
    """
    Full learning cycle:
    1. Sync base knowledge from MD files
    2. Generate a reflection log
    3. Propose an update based on the reflection
    4. Return a structured summary with success/failure flags
    """

    timestamp = datetime.datetime.utcnow()

    # Initialize config + layer
    config = LearningConfig()
    layer = LearningLayer(config)

    # ------------------------------------------------------------
    # LOOP SUMMARY + FAILURE DETECTOR
    # ------------------------------------------------------------
    summary = {
        "md_sync": {"success": False, "error": None},
        "reflection": {"success": False, "error": None},
        "proposal": {"success": False, "error": None},
        "overall_status": "incomplete",
        "timestamp": timestamp.isoformat()
    }

    # ------------------------------------------------------------
    # 1. Sync MD files
    # ------------------------------------------------------------
    try:
        layer.sync_base_knowledge()
        summary["md_sync"]["success"] = True
    except Exception as e:
        summary["md_sync"]["error"] = str(e)

    # ------------------------------------------------------------
    # 2. Generate reflection
    # ------------------------------------------------------------
    reflection = None
    try:
        reflection = layer.generate_reflection(
            user_input="System-triggered learning cycle",
            output="No output — automated learning run",
            timestamp=timestamp
        )
        summary["reflection"]["success"] = True
    except Exception as e:
        summary["reflection"]["error"] = str(e)

    # ------------------------------------------------------------
    # 3. Propose update
    # ------------------------------------------------------------
    proposal = None
