# Run inside `odoo-bin shell`: loads the equipment and inventory sample data
# of the club modules on a database created without Odoo demo data.
#   odoo-bin shell -d <db> < tools/load_sample_equipment.py
from odoo.tools import convert_file

for module, filename in (
        ('amarna_club_assets', 'demo/asset_demo.xml'),
        ('amarna_club_inventory', 'demo/inventory_demo.xml')):
    convert_file(env, module, filename, {}, mode='init', noupdate=True, kind='demo')
env.cr.commit()
print('SAMPLE_EQUIPMENT_LOADED', env['amarna.club.asset'].search_count([]),
      env['amarna.club.inventory.item'].search_count([]))
