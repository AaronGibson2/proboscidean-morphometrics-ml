# Security

Never place API keys in source code, notebooks, configuration files, or command history.
Store local credentials in an ignored `.env` file or in the operating system's environment.

An earlier revision contained a Roboflow key. That credential must be revoked in Roboflow,
even if it appears to work, because deleting it from the current files does not invalidate it
or remove it from Git history. Before publishing the repository, use a history-scanning tool
and remove the historical secret with an appropriate Git history-rewrite procedure.

Report any newly discovered exposed credential to the repository owner privately.
