class {{ classname }}({% block parentclass %}object{% endblock %}):
    """
    {%- block class_doc -%}
    TODO: Write class documentation.
    {%- endblock %}
    """
    {% block class_body %}
    pass
    {% endblock %}