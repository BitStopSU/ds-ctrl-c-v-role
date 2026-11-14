import json
import os

import discord
from discord import app_commands

TOKEN = "дс токен сюда"
TEMPLATES_FILE = "templates.json"


# ---------- работа с файлом шаблонов ----------
def load_templates() -> dict:
    if not os.path.exists(TEMPLATES_FILE):
        return {}
    with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_templates(data: dict) -> None:
    with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------- бот ----------
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    await tree.sync()
    print(f"Бот запущен как {client.user}")


@tree.command(name="save_template", description="Сохранить все роли сервера как шаблон")
@app_commands.describe(name="Название шаблона")
@app_commands.checks.has_permissions(administrator=True)
async def save_template(interaction: discord.Interaction, name: str):
    guild = interaction.guild
    roles = []
    for role in guild.roles:
        # пропускаем @everyone и роли ботов/интеграций (managed)
        if role.is_default() or role.managed:
            continue
        roles.append({
            "name": role.name,
            "color": role.color.value,
            "hoist": role.hoist,            # отдельно в списке участников
            "mentionable": role.mentionable,
            "permissions": role.permissions.value,
            "position": role.position,
        })

    data = load_templates()
    data[name] = {"source_guild": guild.name, "roles": roles}
    save_templates(data)
    await interaction.response.send_message(
        f"Шаблон **{name}** сохранён: {len(roles)} ролей.", ephemeral=True
    )


@tree.command(name="apply_template", description="Создать роли из шаблона на этом сервере")
@app_commands.describe(name="Название шаблона")
@app_commands.checks.has_permissions(administrator=True)
async def apply_template(interaction: discord.Interaction, name: str):
    data = load_templates()
    if name not in data:
        await interaction.response.send_message("Такого шаблона нет.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    existing = {r.name for r in guild.roles}
    created, skipped = 0, 0

    # создаём снизу вверх, чтобы порядок ролей сохранился
    for r in sorted(data[name]["roles"], key=lambda x: x["position"]):
        if r["name"] in existing:
            skipped += 1
            continue
        await guild.create_role(
            name=r["name"],
            colour=discord.Colour(r["color"]),
            hoist=r["hoist"],
            mentionable=r["mentionable"],
            permissions=discord.Permissions(r["permissions"]),
            reason=f"Шаблон {name}",
        )
        created += 1

    await interaction.followup.send(
        f"Готово. Создано: {created}, пропущено (уже есть): {skipped}.\n"
        "Роль бота должна стоять выше создаваемых, иначе порядок может отличаться."
    )


@tree.command(name="list_templates", description="Показать сохранённые шаблоны")
async def list_templates(interaction: discord.Interaction):
    data = load_templates()
    if not data:
        await interaction.response.send_message("Шаблонов пока нет.", ephemeral=True)
        return
    lines = [f"• **{n}** — {len(t['roles'])} ролей (с сервера {t['source_guild']})"
             for n, t in data.items()]
    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@tree.command(name="delete_template", description="Удалить шаблон")
@app_commands.describe(name="Название шаблона")
@app_commands.checks.has_permissions(administrator=True)
async def delete_template(interaction: discord.Interaction, name: str):
    data = load_templates()
    if name not in data:
        await interaction.response.send_message("Такого шаблона нет.", ephemeral=True)
        return
    del data[name]
    save_templates(data)
    await interaction.response.send_message(f"Шаблон **{name}** удалён.", ephemeral=True)


@tree.error
async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("Нужны права администратора.", ephemeral=True)
    else:
        raise error


client.run(TOKEN)
