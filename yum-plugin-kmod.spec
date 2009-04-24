Name:           yum-plugin-kmod
Version: 1.0.0
Release:        1%{?dist}
Summary:        Yum plugin support for kmod kernel modules

Group:          System Environment/Base
License:        GPLv2+
URL:            http://linuxczar.net/wordpress/projects/fedorakmod
Source0:        fedorakmod-%{version}.tar.bz2
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
Requires:       yum

%description
A Yum plugin to support the Fedora Kmod kernel module packaging standard.

%prep
%setup -q -n fedorakmod-%{version}


%build



%install
rm -rf $RPM_BUILD_ROOT

install -m 755 -d %{buildroot}%{_libdir}/yum-plugins
install -m 755 -d %{buildroot}%{_sysconfdir}/yum/pluginconf.d

install -m 644 fedorakmod.py   %{buildroot}%{_libdir}/yum-plugins/
install -m 644 fedorakmod.conf %{buildroot}%{_sysconfdir}/yum/pluginconf.d/


%clean
rm -rf $RPM_BUILD_ROOT


%files
%defattr(-,root,root,-)
%doc README
%{_sysconfdir}/yum/pluginconf.d/*
%{_libdir}/yum-plugins/*


%changelog
* Fri Apr 24 2009 Jack Neely <jjneely@ncsu.edu> 1.0.0-1
- Initial repackaging after removal from yum-utils

