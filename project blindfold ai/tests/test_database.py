from pathlib import Path

from analyzer import analyze_plan
from database import delete_analysis, get_analysis, initialize_database, list_analyses, save_analysis, update_finding_status
from auth import bootstrap_admin, register_user


def test_database_persists_status_and_deletes(tmp_path: Path):
    database = tmp_path / "test.db"
    initialize_database(database)
    bootstrap_admin(database)
    owner_id = register_user("db_user", "db-user@example.test", "DbUserStrongPassword8!", "DbUserStrongPassword8!", database_path=database)
    analysis_id = save_analysis(analyze_plan("I am deploying a website tomorrow.", "website_deployment"), database, owner_id=owner_id)
    loaded = get_analysis(analysis_id, database, owner_id=owner_id)
    assert loaded and loaded["findings"]
    update_finding_status(loaded["findings"][0]["database_id"], "Resolved", database, owner_id=owner_id)
    assert get_analysis(analysis_id, database, owner_id=owner_id)["findings"][0]["status"] == "Resolved"
    delete_analysis(analysis_id, database, owner_id=owner_id)
    assert list_analyses(database, owner_id=owner_id) == []
