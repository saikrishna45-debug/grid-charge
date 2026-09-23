from backend.database.database import SessionLocal
from backend.database.models import SiteConfiguration


def seed_site_configuration():
    """Insert the current residential site configuration."""

    db = SessionLocal()

    try:
        site_id = "SITE-001"

        existing_site = (
            db.query(SiteConfiguration)
            .filter(SiteConfiguration.site_id == site_id)
            .first()
        )

        if existing_site:
            print("SITE CONFIGURATION ALREADY EXISTS")
            print(f"Site ID: {existing_site.site_id}")
            return

        site = SiteConfiguration(
            site_id=site_id,
            site_type="residential",
            grid_capacity_kw=250.0,
            building_peak_demand_kw=190.0,
            solar_capacity_kw=60.0,
            charger_count=50,
        )

        db.add(site)
        db.commit()

        print("=" * 55)
        print("SITE CONFIGURATION SEEDING COMPLETED")
        print("=" * 55)
        print(f"Site ID:              {site.site_id}")
        print(f"Site type:             {site.site_type}")
        print(f"Grid capacity:         {site.grid_capacity_kw:.2f} kW")
        print(f"Building peak demand:  {site.building_peak_demand_kw:.2f} kW")
        print(f"Solar capacity:        {site.solar_capacity_kw:.2f} kW")
        print(f"Charger count:         {site.charger_count}")
        print("=" * 55)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_site_configuration()