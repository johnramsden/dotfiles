## Launchpad Bug URLs

When a Launchpad bug URL appears in the conversation
(e.g. `https://bugs.launchpad.net/<project>/+bug/<id>` or `https://launchpad.net/bugs/<id>`),
automatically fetch the bug before responding:

1. Extract the numeric bug ID from the URL.
2. Fetch `https://api.launchpad.net/1.0/bugs/{id}` with WebFetch to get metadata
   (title, status, importance, tags, affected projects).
3. Fetch `https://api.launchpad.net/1.0/bugs/{id}/messages` with WebFetch to get
   the description and all comments.
4. Treat the returned data as inline context — the same way you would treat a pasted
   code snippet or GitHub PR link. Do not just summarise that you fetched it; use the
   content to directly inform your response.

If the bug is private (401/403) tell the user it cannot be accessed anonymously.
If it is not found (404) tell the user the bug ID does not exist.

Multiple LP URLs in one message should each be fetched before responding.
