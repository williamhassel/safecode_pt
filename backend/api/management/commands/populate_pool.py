from django.core.management.base import BaseCommand
from backend.api.tasks import _generate_one_pooled_challenge, VULNERABILITY_TYPES, POOL_MIN_PER_TYPE
from backend.api.models import GeneratedChallenge


class Command(BaseCommand):
    help = "Pre-generate challenge pool (10 challenges per OWASP type = 100 total)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--per-type",
            type=int,
            default=POOL_MIN_PER_TYPE,
            help="Number of challenges to generate per vulnerability type (default: 10)",
        )
        parser.add_argument(
            "--type",
            dest="vuln_type",
            default=None,
            help="Only generate for this vulnerability type",
        )

    def handle(self, *args, **options):
        per_type = options["per_type"]
        target_types = [options["vuln_type"]] if options["vuln_type"] else VULNERABILITY_TYPES

        self.stdout.write(self.style.NOTICE(
            f"Populating pool: {per_type} challenges x {len(target_types)} types = "
            f"{per_type * len(target_types)} total target"
        ))

        total_added = 0
        for vuln_type in target_types:
            existing = GeneratedChallenge.objects.filter(is_pooled=True, vuln_type=vuln_type).count()
            needed = max(0, per_type - existing)

            if needed == 0:
                self.stdout.write(f"  [{vuln_type}] already has {existing} (skipping)")
                continue

            self.stdout.write(f"  [{vuln_type}] generating {needed} (have {existing})...")
            added = 0
            for i in range(needed):
                ch = _generate_one_pooled_challenge(vuln_type=vuln_type)
                if ch:
                    added += 1
                    self.stdout.write(f"    OK #{ch.id} ({i + 1}/{needed})")
                else:
                    self.stdout.write(self.style.WARNING(f"    FAIL ({i + 1}/{needed})"))

            total_added += added
            self.stdout.write(self.style.SUCCESS(f"  [{vuln_type}] done: {added}/{needed} added"))

        final_total = GeneratedChallenge.objects.filter(is_pooled=True).count()
        self.stdout.write(self.style.SUCCESS(
            f"\nPool population complete. Added {total_added} challenges. "
            f"Total pooled: {final_total}"
        ))
