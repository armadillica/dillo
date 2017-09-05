Dillo 2.0
==========

This branch holds the work in progress on Dillo 2.0, now an extension of [Pillar](https://pillarframework.org/) framework.

Main features to expect in Dillo 2.0:
* Built-in search
* Multi-language support
* Fast. (not that 1.0 was slow, but this is like, crazy fast)

Besides all the bells and whistles, the new Dillo is an extension of the Pillar framework. Pillar is developed and maintained by the Blender Animation Studio, powering services such as [Blender Cloud](https://cloud.blender.org/), [Attract](https://cloud.blender.org/attract), and [Flamenco](https://www.flamenco.io/). Meaning that all the core features (comments, authentication, and so on) will have support and fixes much faster than when Dillo was a stand-alone application, leaving time to develop more Dillo specific features!

## Installation

* Make a config local and add your categories to it:
```
# This list generate the selection menu when creating or editing a post.
POST_CATEGORIES = ['Artwork', 'Tutorials', 'Resources', 'Sneak Peek']
```

* Setup [Algolia](https://www.algolia.com):

Create an account in their site, and add your Algolia API Keys and setup to the config local

```
ALGOLIA_USER="1QFJ16Q4TZ" # Application ID
ALGOLIA_PUBLIC_KEY="039c5c1d0efe9d25d06c00f55a541963" # Search-Only API Key
ALGOLIA_API_KEY="1389947be424f13fbecedabb13ef1710" # Admin API Key
ALGOLIA_INDEX_USERS = 'dev_UsersYourName'
ALGOLIA_INDEX_NODES = 'dev_NodesYourName'
```

* Follow the instructions to install a [Pillar extension](https://https://pillarframework.org/development/install/).
* Initialize dillo for your project

```
python manage.py dillo setup_for_dillo default-project
```

* Create a new post, to populate the Algolia database
* Add the new created categories to your Algolia account:
    * Go to `Dashboard` → `Indices` → `Display` → `Faceting`
    * Select the indice `dev_NodesYourName`
    * `Add an Attribute` →  `"category"`
    * Make it searchable and save it

Credits:
* [Francesco Siddi](https://twitter.com/fsiddi) - Back-end (Dillo & Pillar)
* [Pablo Vazquez](https://twitter.com/PabloVazquez_) - Front-end
* [Dalai Felinto](https://twitter.com/dfelinto) - Multi-Language support
* [Sybren A. Stüvel](https://twitter.com/sastuvel) - Back-end (Pillar)

----
For version 1.0 [check out master](https://github.com/armadillica/dillo).
See it in action [on Blender.Today](http://blender.today).

Follow us [@dillospace](https://twitter.com/dillospace)
