import pillarsdk


def project_submit_menu(project: pillarsdk.Project):
    """Generate the post types menu structure for a project.

    The menu dictionary is passed as a template variable and used to control
    the actual markup.
    """
    dillo_post_node_type = project.get_node_type('dillo_post')
    if not dillo_post_node_type:
        return None
    dillo_post_types = dillo_post_node_type['dyn_schema']['post_type']

    submit_menu = {
        'default': dillo_post_types['default'],
        'allowed': [t for t in dillo_post_types['allowed'] if t != dillo_post_types['default']]
    }

    return submit_menu
