from analyzer import analyze_plan, filter_findings
from components.visualizations import dependency_figure, risk_distribution_chart
from tests.test_analyzer import WEBSITE_DEPLOYMENT_SCENARIO


def test_risk_chart_counts_match_filtered_findings():
    report = analyze_plan(WEBSITE_DEPLOYMENT_SCENARIO, "website_deployment")
    visible = filter_findings(report["findings"], {"Critical", "High"}, None)
    figure = risk_distribution_chart(visible)
    assert sum(figure.data[0].y) == len(visible)
    assert list(figure.data[0].text) == [0, 0, 5, 2]


def test_dependency_graph_uses_short_labels_and_hover_details():
    report = analyze_plan(WEBSITE_DEPLOYMENT_SCENARIO, "website_deployment")
    figure = dependency_figure(report["findings"])
    assert figure is not None
    assert figure.layout.height >= 380
    assert "Backup & restore" in figure.data[1].text
    assert "Dependency relationship" in figure.data[1].hovertext[0]
