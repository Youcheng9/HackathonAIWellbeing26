def generate_explanations(reasons, schedule):
    explanations = []

    for r in reasons:
        if "overloaded days" in r:
            explanations.append(
                f"You have {r.split()[0]} days where your workload exceeds healthy limits."
            )

        elif "weekly workload" in r:
            explanations.append(
                "Your total weekly workload is very high, increasing burnout risk."
            )

        elif "Late-night work" in r:
            explanations.append(
                f"You are working late at night on multiple days, which can disrupt sleep."
            )

        elif "deadlines" in r:
            explanations.append(
                "Several deadlines are grouped closely together, increasing stress."
            )

    return explanations[:3]  # top 3 for UI