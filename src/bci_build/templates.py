import jinja2


DOCKERFILE_TEMPLATE = jinja2.Template(
    """# SPDX-License-Identifier: {{ image.license }}
{% for tag in image.build_tags -%}
#!BuildTag: {{ tag }}
{% endfor -%}

{% if image.from_image is not none %}FROM {% if image.from_image %}{{ image.from_image }}{% else %}suse/sle15:15.{{ image.sp_version }}{% endif %}{% endif %}

MAINTAINER {{ image.maintainer }}

# Define labels according to https://en.opensuse.org/Building_derived_containers
# labelprefix={{ image.labelprefix }}
LABEL org.opencontainers.image.title="{{ image.title }}"
LABEL org.opencontainers.image.description="{{ image.description }}"
LABEL org.opencontainers.image.version="{{ image.version_label }}"
LABEL org.opencontainers.image.url="{{ image.URL }}"
LABEL org.opencontainers.image.created="%BUILDTIME%"
LABEL org.opencontainers.image.vendor="{{ image.VENDOR }}"
LABEL org.opensuse.reference="{{ image.reference }}"
LABEL org.openbuildservice.disturl="%DISTURL%"
LABEL com.suse.supportlevel="{{ image.support_level }}"
LABEL com.suse.eula="sle-bci"
LABEL com.suse.lifecycle-url="https://www.suse.com/lifecycle"
LABEL com.suse.image-type="{{ image.image_type }}"
LABEL com.suse.release-stage="{{ image.release_stage }}"
# endlabelprefix
{% if image.extra_label_lines %}{{ image.extra_label_lines }}{% endif %}

{{ DOCKERFILE_RUN }} zypper -n in --no-recommends {{ image.packages }} && zypper -n clean && rm -rf /var/log/*

{{ image.env_lines }}
{% if image.entrypoint_docker -%}{{ image.entrypoint_docker }}{% endif %}
{% if image.cmd_docker -%}{{ image.cmd_docker }}{% endif %}
{{ image.dockerfile_custom_end }}
"""
)

KIWI_TEMPLATE = jinja2.Template(
    """<?xml version="1.0" encoding="utf-8"?>
<!-- SPDX-License-Identifier: {{ image.license }} -->

<!-- OBS-AddTag: {% for tag in image.build_tags -%} {{ tag }} {% endfor -%}-->
<!-- OBS-Imagerepo: obsrepositories:/ -->

<image schemaversion="6.5" name="{{ image.nvr }}-image" xmlns:suse_label_helper="com.suse.label_helper">
  <description type="system">
    <author>{{ image.VENDOR }}</author>
    <contact>https://www.suse.com/</contact>
    <specification>{{ image.title }}</specification>
  </description>
  <preferences>
    <type image="docker"{% if image.from_image is not none %} derived_from="obsrepositories:/{% if image.from_image %}{{ image.from_image.replace(':', '#') }}{% else %}suse/sle15#15.{{ image.sp_version }}{% endif %}"{% endif %}>
      <containerconfig
          name="{{ image.build_tags[0].split(':')[0] }}"
          tag="{{ image.build_tags[0].split(':')[1] }}"
          maintainer="{{ image.maintainer }}"{% if image.kiwi_additional_tags %}
          additionaltags="{{ image.kiwi_additional_tags }}"{% endif %}>
        <labels>
          <!-- See https://en.opensuse.org/Building_derived_containers#Labels -->
          <suse_label_helper:add_prefix prefix="{{ image.labelprefix }}">
            <label name="org.opencontainers.image.title" value="{{ image.title }}"/>
            <label name="org.opencontainers.image.description" value="{{ image.description }}"/>
            <label name="org.opencontainers.image.version" value="{{ image.version_label }}"/>
            <label name="org.opencontainers.image.created" value="%BUILDTIME%"/>
            <label name="org.opencontainers.image.vendor" value="{{ image.VENDOR }}"/>
            <label name="org.opencontainers.image.url" value="{{ image.URL }}"/>
            <label name="org.opensuse.reference" value="{{ image.reference }}"/>
            <label name="org.openbuildservice.disturl" value="%DISTURL%"/>
            <label name="com.suse.supportlevel" value="{{ image.support_level }}"/>
            <label name="com.suse.image-type" value="{{ image.image_type }}"/>
            <label name="com.suse.eula" value="sle-bci"/>
            <label name="com.suse.release-stage" value="{{ image.release_stage }}"/>
            <label name="com.suse.lifecycle-url" value="https://www.suse.com/lifecycle"/>
{{ image.extra_label_xml_lines }}
          </suse_label_helper:add_prefix>
        </labels>
{% if image.cmd_kiwi %}{{ image.cmd_kiwi }}{% endif %}
{% if image.entrypoint_kiwi %}{{ image.entrypoint_kiwi }}{% endif %}
{{ image.kiwi_env_entry }}
      </containerconfig>
    </type>
    <version>15.{{ image.sp_version }}.0</version>
    <packagemanager>zypper</packagemanager>
    <rpm-check-signatures>false</rpm-check-signatures>
    <rpm-excludedocs>true</rpm-excludedocs>
  </preferences>
  <repository type="rpm-md">
    <source path="obsrepositories:/"/>
  </repository>
{{ image.kiwi_packages }}
</image>
"""
)

SERVICE_TEMPLATE = jinja2.Template(
    """<services>
  <service mode="buildtime" name="kiwi_metainfo_helper"/>
  <service mode="buildtime" name="{{ image.build_recipe_type }}_label_helper"/>
{% for replacement in image.replacements_via_service -%}
  <service name="replace_using_package_version" mode="buildtime">
    <param name="file">{% if (image.build_recipe_type|string) == "docker" %}Dockerfile{% else %}{{ image.package_name }}.kiwi{% endif %}</param>
    <param name="regex">{{ replacement.regex_in_dockerfile }}</param>
    <param name="package">{{ replacement.package_name }}</param>
{% if replacement.parse_version %}    <param name="parse-version">{{ replacement.parse_version }}</param>{% endif %}
  </service>
{% endfor %}
</services>
"""
)
