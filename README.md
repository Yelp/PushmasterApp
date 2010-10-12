An application for pushmasters.


Note: To set up the configuration params that are kept in the datastore
(without which the main app will fail to load), go to /admin/interactive
and run the following script:

    from pushmaster.model import ConfigModel

    c = ConfigModel(
        git_branch_url="""http://gitweb.example.com/?p=reponame.git;a=log;h=refs/heads/%(branch)s""",
        mail_domain="""example.com""",
        mail_request="""request-notifiaction-list@""",
        mail_sender="""pushmaster@""",
        mail_to="""notification-list@""",
        push_plans_url="""http://example.com/path/to/pushplans""",
    )

    c.save()
