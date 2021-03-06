from pyrcb import IRCBot
import redis
import parse

import config

class InfoBot(IRCBot):
    def __init__(self, *args, **kwargs):
        self.r = redis.StrictRedis(host=config.REDIS_HOST,
                                   port=config.REDIS_PORT,
                                   db=config.REDIS_DB,
                                   password=config.REDIS_PASS)

        super().__init__(*args, **kwargs)

    def check_op(self, nickname):
        return (config.IRC_CHAN in self.nicklist and
            nickname in self.nicklist[config.IRC_CHAN] and
            self.nicklist[config.IRC_CHAN][nickname].is_op)

    def add_info(self, nickname, channel, reply_to, info):
        # Add in whois related things to authenticate the user
        # Assumes * is not allowed at the start of nicknames

        info_meta = self.r.get("*" + nickname.lower())
        if info_meta != None:
            info_meta = info_meta.decode("utf-8")

        if info_meta == "frozen":
            if self.check_op(nickname):
                self.r.set(nickname.lower(), info)
                self.send(reply_to, "Set info: " + info)
            else:
                self.send(reply_to, "Only mods can do this.")
        else:
            self.r.set(nickname.lower(), info)
            self.send(reply_to, "Set info: " + info)

    def get_info(self, nickname, channel, reply_to, name_raw):
        name = name_raw.strip()
        if name.startswith("*"):
            self.send(reply_to, "No info found for " + name + ".")
        else:
            info = self.r.get(name.lower())
            if info == None:
                self.send(reply_to, "No info found for " + name + ".")
            else:
                self.send(reply_to, name + ": " + info.decode('utf-8'))

    def delete_info(self, nickname, channel, reply_to, name_raw):
        name = name_raw.strip()
        if self.check_op(nickname):
            if self.r.get(name.lower()) == None:
                self.send(reply_to, "No info found for " + name + ".")
            else:
                self.send(reply_to, "Deleted info for " + name + ".")
                self.r.delete(name.lower())
                self.r.delete("*" + name.lower())
        else:
            self.send(reply_to, "Only mods can do this.")

    def freeze_info(self, nickname, channel, reply_to, name_raw):
        name = name_raw.strip()

        info_meta = self.r.get("*" + name.lower())
        if info_meta != None:
            info_meta = info_meta.decode("utf-8")

        if self.check_op(nickname):
            if info_meta == "frozen":
                self.send(reply_to, "The info for %s was already frozen." % name)
            else:
                self.send(reply_to, "Froze info for " + name + ".")
                self.r.set("*" + name.lower(), "frozen")
        else:
            self.send(reply_to, "Only mods can do this.")

    def unfreeze_info(self, nickname, channel, reply_to, name_raw):
        name = name_raw.strip()

        info_meta = self.r.get("*" + name.lower())
        if info_meta != None:
            info_meta = info_meta.decode("utf-8")

        if self.check_op(nickname):
            if info_meta == "frozen":
                self.send(reply_to, "Unfroze info for %s." % name)
                self.r.set("*" + name.lower(), "")
            else:
                self.send(reply_to, "The info for %s was not frozen." % name)
        else:
            self.send(reply_to, "Only mods can do this.")

    def set_info(self, nickname, channel, reply_to, name_raw, info):
        name = name_raw.strip()
        if self.check_op(nickname):
            self.send(reply_to, "Set info for " + name + ".")
            self.r.set(name.lower(), info)
        else:
            self.send(reply_to, "Only mods can do this.")


    def prompt(self, input_form, output_form):
        def output_func(nick, chan, reply_to, **args):
            self.send(reply_to, str.format(output_form, **args))
       	return (parse.compile(input_form), output_func)

    def on_message(self, message, nickname, channel, is_query):

        #Checks if message was from a PM or channel
        if is_query:
            reply_to = nickname
        else:
            reply_to = channel
        commands = [
                    (parse.compile(".add {info}"), self.add_info),
                    (parse.compile(".info {name_raw}"), self.get_info),
                    (parse.compile(".delete {name_raw}"), self.delete_info),
                    (parse.compile(".freeze {name_raw}"), self.freeze_info),
                    (parse.compile(".unfreeze {name_raw}"), self.unfreeze_info),
                    (parse.compile(".set {name_raw:S} {info}"), self.set_info), # technically this means extra spaces before the name will cause issues...
                    self.prompt(".help", "Try '.info help'"),
                    self.prompt(".add", "Usage: '.add some info about yourself here'"),
                    self.prompt(".info", "Usage: '.info username'"),
                    self.prompt(".delete", "Mod only usage: '.delete username'"),
                    self.prompt(".freeze", "Mod only usage: '.freeze username'"),
                    self.prompt(".unfreeze", "Mod only usage: '.freeze username'"),
                    self.prompt(".set", "Mod only usage: '.set username then some info about them'")
                   ]
        for parser, func in commands:
            attempt = parser.parse(message.strip()) #stripping the message here
            if attempt != None:
                return func(nickname, channel, reply_to, **attempt.named)

    def on_kick(self, nickname, channel, target, message):
        if config.AUTO_REJOIN and self.nickname == target:
            self.join(channel)
            self.send(channel, "%s: I automatically rejoin to prevent people from accidentally kicking me." % nickname)





def main():
    bot = InfoBot()
    bot.connect(config.IRC_HOST, config.IRC_PORT)
    bot.register(config.IRC_USER)
    bot.join(config.IRC_CHAN)
    bot.listen()


if __name__ == "__main__":
    main()
