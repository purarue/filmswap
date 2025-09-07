# filmswap

bot to anonymously swap films with other users to watch

This uses the secret santa verbeage as its familiar. So, you basically set a 'letter', can anonymously communicate back and forth to confirm and then send a gift.

![2024-05-15--14_36_44](https://github.com/purarue/filmswap/assets/7804791/aa3c2ce7-1a08-4f02-a9c7-3e0ace374c6e)

![2024-05-15--14_37_05](https://github.com/purarue/filmswap/assets/7804791/f38537ed-ccc1-4b7a-85cb-419d80dc01e1)

![2024-05-15--14_37_14](https://github.com/purarue/filmswap/assets/7804791/526edaf0-bd70-472a-8634-7ac5b672cc83)

## Installation

Run on `python 3.11.3`

Requires:

- embed links
- attach files
- use slash commands
- send messages
- create public threads
- send messages in threads

Create an `.env` file with values like:

```c
SQLITEDB_PATH="filmswap.db"
SQL_ECHO=0
GUILD_ID=9243234234
ALLOWED_ROLES='["filmswap-mod", "Chat Moderators"]'
ENVIRONMENT=prod
BACKUP_DIR="backups"
APP_LOCALE="film"
PRESENCE_TYPE="watching"
PRESENCE_STATUS="kino, using /help"
```

```bash
git clone https://github.com/purarue/filmswap
cd filmswap
pyenv install 3.11.3
python3 -m pip install virtualenv
python3 -m virtualenv .venv -p ~/.pyenv/versions/3.11.3/bin/python
# to develop/work in environment: source activate:
# (you should do this whenever interacting with the bot/dependencies)
source ./.venv/bin/activate
# to leave, type 'deactivate'
pip install -r ./requirements.txt
pip install .
# once all is installed:
# generate locales if necessary:
make
# run the bot
./scripts/run-bot
# or ./.venv/bin/python -m filmswap run
```

The `requirements.txt` is updated by adding something to `requirements.in` and then using `pip-compile >requirements.txt` (`pip install pip-tools` if command is missing)

This runs a swap as a singleton, adding multiple swaps per server was originally supported but it makes the commands a bit more complicated, and I don't think its worth the complication.
To create a swap, run `/create`, then `/set-channel`, then `/send-join-message` to send a message to the channel to join the swap.

Once users have joined then can set their `>letter`s telling the bot what they want to watch

Then, `/set-period SWAP` will start the SWAP period, matching users up with santa/giftee pairs, users can then use `/read` and `>submit` to read and submit their films, and `>write-giftee`/`>write-santa` to anonymously communicate with their giftee/santas

If people join late, you can use admin `match-users` command to match them up with other users who joined late (Requires at least 2 late joiners)

Then, once all the films are submitted, you can use `/set-period WATCH` to start the watch period, where users can watch the films they were given, and use `/done-watching` to mark them as watched (or an admin can use `/set-user-done-watching` to do so)

The admin/`filmswap-manage` commands automatically work if a user is an admin, but can also be controlled through one or more roles

## DB-Backups

This makes backups of the databases when switching back to the JOIN period (so, at the end of each swap), and saves them in `./backups`. You can also manually trigger a backup. To restore from a backup file:

```bash
# shut down bot
rm -v *.db*  # remove database and any temporary shared memory/log files for the db
mv ./backups/1712699606.sqlite ./filmswap.db  # replace database with the newest file
# restart bot
```

## Migrations

This doesn't support an ORM or complex migration tool, it just uses SQLite files that you have to run against the database when things change. If you recently set up the bot you don't have to run any migrations, if there are ones added recently in ./migrations/ then you can use the ./migrations/run_migration script to run it against your database (would recommend making a backup first)

## Localization

This uses `gettext` to allow strings in the application to be localized, so this could be used for something other than films (e.g. manga, books etc.)

To set the language, set the `APP_LOCALE` in your `.env` file, e.g., `APP_LOCALE="manga"`

See the [`Makefile`](./Makefile) for commands that get run, but basically to add a new type, you'd do:

```bash
make clean
make
cp ./messages/reference.pot ./messages/books.pot
# whenever there are changes made in code that adds new strings
# that need to be localized, you can run this command to merge:
msgmerge -U ./messages/books.pot ./messages/reference.pot
# and then to compile it into a binary file that gets loaded at runtime:
pybabel compile -i ./messages/books.pot -o ./locales/en_US/LC_MESSAGES/books.mo
```

Make sure you have one of these environment variables set (**not in the .env file**, before you start the bot):

- `LANGUAGE`
- `LC_ALL`
- `LC_MESSAGES`
- `LANG`

to something like `en_US` or `en_US.UTF-8`

In code, strings that can be translated are marked like `_("Filmswap Help")`. The `_` is an alias to the stdlib [`gettext.gettext`](https://docs.python.org/3/library/gettext.html) function. If something should be localized but isn't, feel free to create an Issue/PR.

After modifying any of the `./messages` file, run `make` in the root directory to update the generated `./locales` binary files. Those are then loaded when the bot starts.

Troubleshooting:

- If the `./reference.pot` file doesn't seem to be being generated, try `make clean && touch ./filmswap/__init__.py && make`
- You should be modifying the `msgstr` to the translated value, see [`messages/manga.pot`](./messages/manga.pot) as an example
