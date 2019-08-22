from handler import BaseCommand, Context, Arguments, CommandResult

from rpg.player import Player, UnknownPlayer
from utils.formatting import codeblock

class Command(BaseCommand):
    async def run(self, ctx: Context, args: Arguments) -> CommandResult:
        try:
            player = await Player.from_id(ctx.author.id, ctx.bot.pg)
        except UnknownPlayer:
            return "У вас нет персонажа"

        if not player.inventory.size:
            return "Ваш инвентарь пуст"

        sq = []
        for i in player.inventory:
            sq.append(str(i))

        return codeblock("\n".join(str(i) + ' x ' + str(sq.count(i)) for i in set(sq)))
