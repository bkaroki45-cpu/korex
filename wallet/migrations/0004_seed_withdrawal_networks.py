from django.db import migrations


NETWORKS = (
    ("TRC20", "TRON (TRC20)"), ("ERC20", "Ethereum (ERC20)"),
    ("BEP20", "BNB Smart Chain (BEP20)"), ("POLYGON", "Polygon"),
    ("SOLANA", "Solana"), ("ARBITRUM", "Arbitrum One"),
    ("OPTIMISM", "Optimism"), ("AVALANCHE", "Avalanche C-Chain"),
    ("BASE", "Base"), ("BITCOIN", "Bitcoin"), ("LITECOIN", "Litecoin"),
    ("XRP", "XRP Ledger"), ("STELLAR", "Stellar"), ("TON", "TON"),
    ("SUI", "Sui"), ("APTOS", "Aptos"), ("CARDANO", "Cardano"),
    ("ALGORAND", "Algorand"), ("COSMOS", "Cosmos"), ("NEAR", "NEAR Protocol"),
)


def seed_networks(apps, schema_editor):
    WithdrawalNetwork = apps.get_model("wallet", "WithdrawalNetwork")
    for code, name in NETWORKS:
        WithdrawalNetwork.objects.get_or_create(code=code, defaults={"name": name, "is_enabled": True})


class Migration(migrations.Migration):
    dependencies = [("wallet", "0003_platformconfiguration_withdrawalnetwork_and_more")]
    operations = [migrations.RunPython(seed_networks, migrations.RunPython.noop)]
