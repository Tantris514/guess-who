"""The shop catalogue, shared by s34_shop.py (server prices, names), u17_shop_ui.py (the menu card) and u15 (dev menu).
Pure data: no unreal import. Vendor kinds: 0 the barman (billiard-room bar), 1 the junkie (toilets, shadier prices, the
only one selling the firecracker), 2 a waiter (walking, barman prices)."""

# id, name, short description, barman price, junkie price, key shown, hint after a purchase
ITEMS = [
    (1, 'Vieux fusil', "Long, une seule balle, difficile à viser : le viseur bouge. Clic droit pour viser.", 150, 180, 'Clic', 'clic droit pour viser, clic gauche pour tirer'),
    (2, 'Bombe fumigène', 'Lancée devant vous : un épais nuage pendant 18 s.', 40, 30, 'Clic', 'sélectionnez-la, clic gauche'),
    (4, 'Gaz rétrécissant', 'Petit et rapide pendant 20 s.', 60, 45, 'Clic', 'sélectionnez-le, clic gauche'),
    (5, 'Piège', "Dans une porte ou par terre : saute au passage d'un joueur (-50 PV) ou d'un intrus, jamais d'un simple invité.", 80, 60, 'Clic', 'sélectionnez-le, clic gauche'),
    (6, 'Bombe', 'Bip-bip… 45 s, puis une énorme explosion. Désamorçable.', 120, 90, 'Clic', 'sélectionnez-la, clic gauche'),
    (7, 'Munitions de tourelle', '60 balles pour la tourelle de la mezzanine.', 80, 100, '—', 'pour la tourelle'),
    (8, "Pistolet d'échange", 'Visez un invité : vous prenez son corps. Se recharge.', 200, 240, 'Clic', 'sélectionnez-le, clic gauche'),
    (9, 'Pétard', 'Lancé, il crépite comme une fusillade 4 s plus tard. Le leurre parfait.', 0, 30, 'Clic', 'sélectionnez-le, clic gauche'),
    (14, 'Mascarade', "Tous les invités, vous compris, changent d'apparence au hasard.", 150, 120, 'Clic', 'sélectionnez-la, clic gauche'),
    (10, 'Lame secrète',"Cachée dans la manche. Tue un invité ou un rival d'un coup, sans un bruit. Se recharge 8 s.", 180, 150, 'Clic', 'sélectionnez-la, clic gauche tout près'),
]
# inventory ids beyond the catalogue: 3 the flashlight (no longer sold, the user, 2026-11-05: loot, mystery box, dev menu only),
# 11 balls, 12 sword, 13 the detective's revolver (s40_inventory.py); s40_gm's ShopBuy refuses 3 and 11-13
MAX_ID = 14
JUNKIE_ONLY = {9}
# vendor kind -> (title, line under the title, floating prompt)
VENDORS = {
    0: ("LE BAR D'ASHCOMBE", '« Qu’est-ce que je vous sers ? »  — le barman', 'Le barman (boutique)'),
    1: ('LE MARCHÉ NOIR', '« Psst… Pas de questions, pas de reçu. »  — le junkie', 'Le junkie (marché noir)'),
    2: ('LE PLATEAU DU SERVEUR', '« Monsieur désire ? »  — le serveur', 'Le serveur (boutique)'),
}


def price(item_id, kind):
    it = next(i for i in ITEMS if i[0] == item_id)
    return it[4] if kind == 1 else it[3]


# Graph bodies written by s40_inventory.py: the older owner scripts skip these names, so re-running them keeps the inventory
# (always run s40 after s12/s13/s33/s34/s35/s38). Item 13 of the 2026-11-03 feedback list: see s40's docstring.
S40_OWNS = {
    'OnCharacterShot', 'RequestFire', 'GWFire', 'ShopTick', 'SurviveTick', 'ShopBuy', 'ShopCleanup', 'GuestShoot', 'GuestHit', 'GunFor',
    'TrapTick', 'TrapFire', 'PlaceTrap', 'TurretHit', 'PullAlarm', 'TakePickup', 'SyncSword', 'NearPickupFor', 'PickupNotices',
    'FPItemsTick', 'GWGuestAttack', 'RequestUse', 'ToggleLamp', 'LampTick', 'CanShop', 'PromptPick', 'ShopClientTick', 'GuestFire',
    'GWUseItem', 'GWDevGive', 'DefuseRelease',
    'ItemPrice', 'ItemName',
    # last one standing (s46_last_standing.py owns these; run it after s32/s34/s38 and before s40)
    'WeaponHit', 'SlashTarget', 'HurtCharacter', 'DefuseOk', 'DefuseBomb',
}
