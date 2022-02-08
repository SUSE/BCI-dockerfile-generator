import jinja2


DOCKERFILE_TEMPLATE = jinja2.Template(
    """{% for tag in image.build_tags -%}
#!BuildTag: {{ tag }}
{% endfor -%}

FROM {% if image.from_image %}{{ image.from_image }}{% else %}suse/sle15:15.{{ sp_version }}{% endif %}

MAINTAINER {{ image.maintainer }}

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix={{ image.labelprefix }}
PREFIXEDLABEL org.opencontainers.image.title="{{ image.title }}"
PREFIXEDLABEL org.opencontainers.image.description="{{ image.description }}"
PREFIXEDLABEL org.opencontainers.image.version="{{ image.version_label }}"
PREFIXEDLABEL org.opencontainers.image.url="https://www.suse.com/products/server/"
PREFIXEDLABEL org.opencontainers.image.created="%BUILDTIME%"
PREFIXEDLABEL org.opencontainers.image.vendor="SUSE LLC"
PREFIXEDLABEL org.opensuse.reference="{{ image.reference }}"
PREFIXEDLABEL org.openbuildservice.disturl="%DISTURL%"
{% if image.tech_preview -%}PREFIXEDLABEL com.suse.techpreview="true"{% endif %}
PREFIXEDLABEL com.suse.eula="sle-bci"
PREFIXEDLABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
PREFIXEDLABEL com.suse.image-type="{{ image.image_type }}"
PREFIXEDLABEL com.suse.release-stage="{{ image.release_stage }}"
# endlabelprefix
{% if image.extra_label_lines %}{{ image.extra_label_lines }}{% endif %}

RUN zypper -n in --no-recommends {{ image.packages }} && zypper -n clean && rm -rf /var/log/*

{{ image.env_lines }}
{% if image.entrypoint -%}ENTRYPOINT {{ image.entrypoint }}{% endif %}
{{ image.custom_end }}
"""
)


SERVICE_TEMPLATE = jinja2.Template(
    """<services>
  <service mode="buildtime" name="kiwi_metainfo_helper"/>
  <service mode="buildtime" name="docker_label_helper"/>
{% for replacement in image.replacements_via_service -%}
  <service name="replace_using_package_version" mode="buildtime">
    <param name="file">Dockerfile</param>
    <param name="regex">{{ replacement.regex_in_dockerfile }}</param>
    <param name="package">{{ replacement.package_name }}</param>
{% if replacement.parse_version %}    <param name="parse-version">{{ replacement.parse_version }}</param>{% endif %}
  </service>
{% endfor %}
</services>
"""
)
